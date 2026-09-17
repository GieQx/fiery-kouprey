from __future__ import annotations

from pydantic import BaseModel, Field, computed_field


class ArtefactRef(BaseModel):
    agency_id: str | None = None
    id: str
    version: str | None = None
    maintainable_parent_id: str | None = None

    @computed_field
    @property
    def key(self) -> str:
        agency = self.agency_id or "_"
        version = self.version or "_"
        return f"{agency}:{self.id}({version})"


class Representation(BaseModel):
    kind: str
    enumeration: ArtefactRef | None = None
    facets: dict[str, str] = Field(default_factory=dict)


class Code(BaseModel):
    id: str
    names: dict[str, str] = Field(default_factory=dict)
    descriptions: dict[str, str] = Field(default_factory=dict)
    source_path: str

    @computed_field
    @property
    def label(self) -> str:
        return self.names.get("en") or next(iter(self.names.values()), self.id)


class Codelist(BaseModel):
    ref: ArtefactRef
    names: dict[str, str] = Field(default_factory=dict)
    descriptions: dict[str, str] = Field(default_factory=dict)
    codes: list[Code] = Field(default_factory=list)
    source_path: str

    @computed_field
    @property
    def label(self) -> str:
        return self.names.get("en") or next(iter(self.names.values()), self.ref.id)


class Component(BaseModel):
    component_type: str
    id: str
    position: int | None = None
    names: dict[str, str] = Field(default_factory=dict)
    descriptions: dict[str, str] = Field(default_factory=dict)
    concept_ref: ArtefactRef | None = None
    codelist_ref: ArtefactRef | None = None
    representation: Representation | None = None
    annotations: list[str] = Field(default_factory=list)
    source_path: str

    @computed_field
    @property
    def label(self) -> str:
        return self.names.get("en") or next(iter(self.names.values()), self.id)

    @computed_field
    @property
    def description(self) -> str:
        return self.descriptions.get("en") or next(iter(self.descriptions.values()), "")


class DSDStructure(BaseModel):
    agency_id: str | None = None
    id: str
    version: str | None = None
    names: dict[str, str] = Field(default_factory=dict)
    descriptions: dict[str, str] = Field(default_factory=dict)
    dimensions: list[Component] = Field(default_factory=list)
    attributes: list[Component] = Field(default_factory=list)
    codelists: dict[str, Codelist] = Field(default_factory=dict)
    file_name: str

    @computed_field
    @property
    def label(self) -> str:
        return self.names.get("en") or next(iter(self.names.values()), self.id)

    def find_codelist(self, ref: ArtefactRef | None) -> Codelist | None:
        if ref is None:
            return None
        if ref.key in self.codelists:
            return self.codelists[ref.key]
        return next((item for item in self.codelists.values() if item.ref.id == ref.id), None)

