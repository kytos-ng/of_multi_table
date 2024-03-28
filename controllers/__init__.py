"""PipelineController"""

# pylint: disable=unnecessary-lambda,invalid-name,unnecessary-comprehension
import os
from datetime import datetime
from typing import Dict, Optional
from uuid import uuid4

from pydantic import ValidationError
from pymongo.collection import ReturnDocument
from pymongo.errors import AutoReconnect
from pymongo.results import InsertOneResult
from tenacity import retry_if_exception_type, stop_after_attempt, wait_random

from kytos.core.db import Mongo
from kytos.core.retry import before_sleep, for_all_methods, retries
from napps.kytos.of_multi_table.db.models import PipelineBaseDoc
from napps.kytos.of_multi_table.status import PipelineStatus


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
            self.db.pipelines.insert_one(
                PipelineBaseDoc(
                    **{
                        "_id": _id,
                        **pipeline,
                        "inserted_at": utc_now,
                        "updated_at": utc_now,
                    }
                ).model_dump(exclude_none=True)
            )
        except ValidationError as err:
            raise err
        return _id

    def get_active_pipeline(self) -> Dict:
        """Get a pipeline that is not disabled."""
        return (
            self.db.pipelines.find_one(
                {"status": {"$ne": PipelineStatus.DISABLED.value}}
            )
            or {}
        )

    def get_pipelines(self, status: str = None) -> Dict:
        """Get a list of pipelines"""
        match_filters = {"$match": {}}
        if status:
            match_filters["$match"]["status"] = status.lower()
        result = self.db.pipelines.aggregate(
            [
                {
                    "$project": PipelineBaseDoc.projection(),
                },
                match_filters,
            ]
        )
        return {"pipelines": [pipeline for pipeline in result]}

    def get_pipeline(self, id_: str) -> Optional[Dict]:
        """Get a single pipeline"""
        return self.db.pipelines.find_one({"_id": id_}, PipelineBaseDoc.projection())

    def delete_pipeline(self, id_: str) -> int:
        """Delete a pipeline"""
        return self.db.pipelines.delete_one({"id": id_}).deleted_count

    def enabling_pipeline(self, id_: str) -> Optional[Dict]:
        """Change pipeline status to enabling"""
        utc_now = datetime.utcnow()
        pipeline = self.db.pipelines.find_one_and_update(
            {"id": id_},
            {"$set": {"status": PipelineStatus.ENABLING.value, "updated_at": utc_now}},
            return_document=ReturnDocument.AFTER,
        )
        if not pipeline:
            return pipeline
        self.db.pipelines.find_one_and_update(
            {"status": {"$ne": "disabled"}, "id": {"$ne": id_}},
            {"$set": {"status": "disabled", "updated_at": utc_now}},
        )
        return pipeline

    def enabled_pipeline(self, id_: str) -> Optional[Dict]:
        """Change pipeline status to enabled"""
        utc_now = datetime.utcnow()
        pipeline = self.db.pipelines.find_one_and_update(
            {"id": id_},
            {"$set": {"status": PipelineStatus.ENABLED.value, "updated_at": utc_now}},
            return_document=ReturnDocument.AFTER,
        )
        return pipeline

    def disabling_pipeline(self, id_: str) -> Optional[Dict]:
        """Change pipeline status to disabling"""
        utc_now = datetime.utcnow()
        pipeline = self.db.pipelines.find_one_and_update(
            {"id": id_},
            {"$set": {"status": PipelineStatus.DISABLING.value, "updated_at": utc_now}},
            return_document=ReturnDocument.BEFORE,
        )
        return pipeline

    def disabled_pipeline(self, id_: str) -> Optional[Dict]:
        """Change pipeline status to disabled
        ReturnDocument set to before to check if actions are needed
        if it was disabled, no need to analyze flows"""
        utc_now = datetime.utcnow()
        pipeline = self.db.pipelines.find_one_and_update(
            {"id": id_},
            {"$set": {"status": PipelineStatus.DISABLED.value, "updated_at": utc_now}},
            return_document=ReturnDocument.BEFORE,
        )
        return pipeline

    def error_pipeline(self, id_: str, status: str) -> Dict:
        """Add '-error' to the current status"""
        utc_now = datetime.utcnow()
        pipeline = self.db.pipelines.find_one_and_update(
            {"id": id_},
            {"$set": {"status": status, "updated_at": utc_now}},
            return_document=ReturnDocument.BEFORE,
        )
        return pipeline
