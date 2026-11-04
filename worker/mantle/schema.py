from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Profile = Literal["rounded", "oval", "faceted"]
Fullness = Literal["close", "balanced", "generous"]
Taper = Literal["none", "toward-end", "toward-base"]
EndCoverage = Literal["short", "standard", "long"]
PanelLayout = Literal["single-shell", "lengthwise-split", "band-and-body"]
Seam = Literal["tight", "shadow", "open"]
Access = Literal["none", "side", "end"]
Finish = Literal["matte-white", "matte-black", "soft-gray"]


class Decisions(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    profile: Profile = "rounded"
    fullness: Fullness = "balanced"
    taper: Taper = "none"
    end_coverage: EndCoverage = Field("standard", alias="end-coverage")
    panel_layout: PanelLayout = Field("lengthwise-split", alias="panel-layout")
    seam: Seam = "shadow"
    access_panel: Access = Field("none", alias="access-panel")
    finish: Finish = "matte-white"

    def geometry_key(self) -> tuple:
        data = self.model_dump(by_alias=True)
        data.pop("finish")
        return tuple(sorted(data.items()))


class Applied(BaseModel):
    decision: str
    value: str
    source: str


class Proposal(BaseModel):
    name: str
    rationale: str
    decisions: Decisions
    applied: list[Applied]
    locks: list[str]
