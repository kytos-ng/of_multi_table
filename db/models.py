"""DB Models"""
# pylint: disable=no-self-argument,invalid-name,no-name-in-module
from datetime import datetime
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, conint, root_validator, validator


class DocumentBaseModel(BaseModel):
    """Base model for Mongo documents"""

    id: str = Field(None, alias="_id")
    inserted_at: Optional[datetime]
    updated_at: Optional[datetime]

    def dict(self, **kwargs) -> Dict:
        """Return a dictionary representation of the model"""
        values = super().dict(**kwargs)
        if "id" in values and values["id"]:
            values["_id"] = values["id"]
        if "exclude" in kwargs and "_id" in kwargs["exclude"]:
            del values["_id"]
        return values


class MatchSubDoc(BaseModel):
    """Match DB SubDocument Model."""

    in_port: Optional[int]
    dl_src: Optional[str]
    dl_dst: Optional[str]
    dl_type: Optional[int]
    dl_vlan: Optional[Union[int, str]]
    dl_vlan_pcp: Optional[int]
    nw_src: Optional[str]
    nw_dst: Optional[str]
    nw_proto: Optional[int]
    tp_src: Optional[int]
    tp_dst: Optional[int]
    in_phy_port: Optional[int]
    ip_dscp: Optional[int]
    ip_ecn: Optional[int]
    udp_src: Optional[int]
    udp_dst: Optional[int]
    sctp_src: Optional[int]
    sctp_dst: Optional[int]
    icmpv4_type: Optional[int]
    icmpv4_code: Optional[int]
    arp_op: Optional[int]
    arp_spa: Optional[str]
    arp_tpa: Optional[str]
    arp_sha: Optional[str]
    arp_tha: Optional[str]
    ipv6_src: Optional[str]
    ipv6_dst: Optional[str]
    ipv6_flabel: Optional[int]
    icmpv6_type: Optional[int]
    icmpv6_code: Optional[int]
    nd_tar: Optional[int]
    nd_sll: Optional[int]
    nd_tll: Optional[int]
    mpls_lab: Optional[int]
    mpls_tc: Optional[int]
    mpls_bos: Optional[int]
    pbb_isid: Optional[int]
    v6_hdr: Optional[int]
    metadata: Optional[int]
    tun_id: Optional[int]

    @validator("dl_vlan")
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
    instructions: Optional[List[dict]]
    match: Optional[MatchSubDoc]


class MultitableDoc(BaseModel):
    """Base model for Multitable"""

    table_id: conint(ge=0, le=254)
    table_miss_flow: Optional[TableMissDoc]
    description: Optional[str]
    napps_table_groups: Optional[dict[str, List[str]]]

    @root_validator
    def validate_intructions(cls, values):
        """Validate intructions"""
        table_miss_flow = values.get("table_miss_flow")
        if not table_miss_flow:
            return values
        table_id = values["table_id"]
        instructions = table_miss_flow.dict(exclude_none=True)["instructions"]
        for instruction in instructions:
            miss_table_id = instruction.get("table_id")
            if miss_table_id is not None and miss_table_id <= table_id:
                msg = (
                    f"Table {table_id} has a lower or equal "
                    f"table_id {miss_table_id} in instructions"
                )
                raise ValueError(msg)
        return values


class PipelineBaseDoc(DocumentBaseModel):
    """Base model for Pipeline documents"""

    status = "disabled"
    multi_table: List[MultitableDoc]

    @validator("multi_table")
    def validate_table_groups(cls, pipeline):
        """Validate table groups"""
        content = {}
        id_set = set()
        for table in pipeline:
            table_dict = table.dict(exclude_none=True)
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
