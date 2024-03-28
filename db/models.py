"""DB Models"""

# pylint: disable=no-self-argument,invalid-name,no-name-in-module
from datetime import datetime
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Annotated


class DocumentBaseModel(BaseModel):
    """Base model for Mongo documents"""

    id: str = Field(None, alias="_id")
    inserted_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def model_dump(self, **kwargs) -> Dict:
        """Return a dictionary representation of the model"""
        values = super().model_dump(**kwargs)
        if "id" in values and values["id"]:
            values["_id"] = values["id"]
        if "exclude" in kwargs and "_id" in kwargs["exclude"]:
            del values["_id"]
        return values


class MatchSubDoc(BaseModel):
    """Match DB SubDocument Model."""

    in_port: Optional[int] = None
    dl_src: Optional[str] = None
    dl_dst: Optional[str] = None
    dl_type: Optional[int] = None
    dl_vlan: Optional[Union[int, str]] = None
    dl_vlan_pcp: Optional[int] = None
    nw_src: Optional[str] = None
    nw_dst: Optional[str] = None
    nw_proto: Optional[int] = None
    tp_src: Optional[int] = None
    tp_dst: Optional[int] = None
    in_phy_port: Optional[int] = None
    ip_dscp: Optional[int] = None
    ip_ecn: Optional[int] = None
    udp_src: Optional[int] = None
    udp_dst: Optional[int] = None
    sctp_src: Optional[int] = None
    sctp_dst: Optional[int] = None
    icmpv4_type: Optional[int] = None
    icmpv4_code: Optional[int] = None
    arp_op: Optional[int] = None
    arp_spa: Optional[str] = None
    arp_tpa: Optional[str] = None
    arp_sha: Optional[str] = None
    arp_tha: Optional[str] = None
    ipv6_src: Optional[str] = None
    ipv6_dst: Optional[str] = None
    ipv6_flabel: Optional[int] = None
    icmpv6_type: Optional[int] = None
    icmpv6_code: Optional[int] = None
    nd_tar: Optional[int] = None
    nd_sll: Optional[int] = None
    nd_tll: Optional[int] = None
    mpls_lab: Optional[int] = None
    mpls_tc: Optional[int] = None
    mpls_bos: Optional[int] = None
    pbb_isid: Optional[int] = None
    v6_hdr: Optional[int] = None
    metadata: Optional[int] = None
    tun_id: Optional[int] = None

    @field_validator("dl_vlan")
    @classmethod
    def vlan_with_mask(cls, v):
        """Validate vlan format"""
        try:
            return int(v)
        except ValueError:
            try:
                [int(part) for part in v.split("/")]
            except ValueError:
                raise ValueError(
                    "must be an integer or an integer with a mask in format vlan/mask"
                )
        return v


class TableMissDoc(BaseModel):
    """Base model for Table miss flow"""

    priority: int
    instructions: Optional[List[dict]] = None
    match: Optional[MatchSubDoc] = None


class MultitableDoc(BaseModel):
    """Base model for Multitable"""

    table_id: Annotated[int, Field(ge=0, le=254)]
    table_miss_flow: Optional[TableMissDoc] = None
    description: Optional[str] = None
    napps_table_groups: Optional[dict[str, List[str]]] = None

    @model_validator(mode="after")
    def validate_intructions(self):
        """Validate intructions"""
        table_miss_flow = self.table_miss_flow
        if not table_miss_flow:
            return self
        table_id = self.table_id
        instructions = table_miss_flow.model_dump(exclude_none=True)["instructions"]
        for instruction in instructions:
            miss_table_id = instruction.get("table_id")
            if miss_table_id is not None and miss_table_id <= table_id:
                msg = (
                    f"Table {table_id} has a lower or equal "
                    f"table_id {miss_table_id} in instructions"
                )
                raise ValueError(msg)
        return self


class PipelineBaseDoc(DocumentBaseModel):
    """Base model for Pipeline documents"""

    status: str = "disabled"
    multi_table: List[MultitableDoc]

    @field_validator("multi_table")
    @classmethod
    def validate_table_groups(cls, pipeline):
        """Validate table groups"""
        content = {}
        id_set = set()
        for table in pipeline:
            table_dict = table.model_dump(exclude_none=True)
            table_groups = table_dict.get("napps_table_groups", {})
            table_id = table_dict["table_id"]
            if table_id in id_set:
                msg = f"Table id {table_id} repeated"
                raise ValueError(msg)
            id_set.add(table_id)
            for napp in table_groups:
                if napp not in content:
                    content[napp] = set(table_groups[napp])
                else:
                    repeated = content[napp] & set(table_groups[napp])
                    if repeated:
                        msg = (
                            f"Repeated {napp} table groups, {repeated}"
                            f" in table id: {table_id}"
                        )
                        raise ValueError(msg)
                    content[napp] |= set(table_groups[napp])
        return pipeline

    @staticmethod
    def projection() -> dict:
        """Base model for projection"""
        return {
            "_id": 0,
            "id": 1,
            "multi_table": 1,
            "status": 1,
            "inserted_at": 1,
            "updated_at": 1,
        }
