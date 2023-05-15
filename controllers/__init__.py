import os
from datetime import datetime
from uuid import uuid4
from typing import Optional, Dict
from pydantic import ValidationError
from pymongo.collection import ReturnDocument
from pymongo.errors import AutoReconnect
from pymongo.results import InsertOneResult
from tenacity import retry_if_exception_type, stop_after_attempt, wait_random

from kytos.core.db import Mongo
from kytos.core.retry import before_sleep, for_all_methods, retries

from napps.kytos.of_multi_table.db.models import PipelineBaseDoc


@for_all_methods(
    retries,
    stop=stop_after_attempt(
        int(os.environ.get("MONGO_AUTO_RETRY_STOP_AFTER_ATTEMPT", 3))
    ),
    wait=wait_random(
        min=int(os.environ.get("MONGO_AUTO_RETRY_WAIT_RANDOM_MIN", 0.1)),
        max=int(os.environ.get("MONGO_AUTO_RETRY_WAIT_RANDOM_MAX", 1)),
    ),
    before_sleep=before_sleep,
    retry=retry_if_exception_type((AutoReconnect,)),
)
class PipelineController:
    """PipelineController"""

    def __init__(self, get_mongo=lambda: Mongo()) -> None:
        """FlowController."""
        self.mongo = get_mongo()
        self.db_client = self.mongo.client
        self.db = self.db_client[self.mongo.db_name]

    def insert_pipeline(self, pipeline: Dict) -> InsertOneResult:
        """Insert a pipeline"""
        utc_now = datetime.utcnow()
        _id = str(uuid4().hex)
        try:
            self.db.pipelines.insert_one(PipelineBaseDoc(**{
                "_id": _id,
                **pipeline,
                "inserted_at": utc_now,
                "updated_at": utc_now,
            }).dict(exclude_none=True))
        except ValidationError as err:
            raise err
        return _id
    
    def get_pipelines(self, status: str = None) -> Dict:
        """Get a list of pipelines"""
        match_filters = {"$match": {}}
        if status:
            match_filters["$match"]["status"] = status.lower()
        result = self.db.pipelines.aggregate([{
                "$project": PipelineBaseDoc.projection(),
            },
            match_filters
        ])
        return {"pipelines": [pipeline for pipeline in result]}
    
    def get_pipeline(self, id: str) -> Optional[Dict]:
        """Get a single pipeline"""
        return self.db.pipelines.find_one(
            {"_id": id},
            PipelineBaseDoc.projection()
        )
    
    def delete_pipeline(self, id: str) -> int:
        """Delete a pipeline"""
        return self.db.pipelines.delete_one({"id": id}).deleted_count

    def enabling_pipeline(self, id: str) -> Optional[Dict]:
        """Change pipeline status to enabling"""
        utc_now = datetime.utcnow()
        pipeline = self.db.pipelines.find_one_and_update(
            {"id": id},
            {"$set": {"status": "enabling", "updated_at": utc_now}},
            return_document=ReturnDocument.AFTER
        )
        if not pipeline:
            return pipeline
        self.db.pipelines.find_one_and_update(
                {"status": "enabled", "id": {"$ne": id}},
                {"$set": {"status": "disabled", "updated_at": utc_now}}
        )
        return pipeline

    def enabled_pipeline(self, id: str) -> Optional[Dict]:
        """Change pipeline status to enabled"""
        utc_now = datetime.utcnow()
        pipeline = self.db.pipelines.find_one_and_update(
            {"id": id},
            {"$set": {"status": "enabled", "updated_at": utc_now}},
            return_document=ReturnDocument.AFTER
        )
        return pipeline

    def disabled_pipeline(self, id: str) -> Optional[Dict]:
        """Change pipeline status to disabled
        ReturnDocument set to before to check if actions are needed
        if it was disabled, no need to analyze flows"""
        utc_now = datetime.utcnow()
        pipeline = self.db.pipelines.find_one_and_update(
            {"id": id},
            {"$set": {"status": "disabled", "updated_at": utc_now}},
            return_document=ReturnDocument.BEFORE
        )
        return pipeline
    
    def get_last_updated(self) -> Dict:
        """Get last updated pipeline
        Only used to return to previous enabled pipeline"""
        pipelines = self.db.pipelines.find().sort("updated_at", -1)
        return pipelines.next()
