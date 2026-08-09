from pydantic import BaseModel, ConfigDict, Field


class SignupRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    nickname: str = Field(min_length=1, max_length=50)


class LoginRequest(BaseModel):
    email: str
    password: str


class GenderVerificationRequest(BaseModel):
    test_code: str = Field(min_length=1, max_length=100)


class ReviewPhotoInput(BaseModel):
    photo_data: str = Field(min_length=1)
    photo_name: str | None = Field(default=None, max_length=255)


class ReviewCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    lat: float
    lng: float
    user_score: int = Field(ge=0, le=5)
    photos: list[ReviewPhotoInput] = Field(default_factory=list, max_length=5)
    photo_data: str | None = None
    photo_name: str | None = Field(default=None, max_length=255)


class ReviewUpdate(BaseModel):
    content: str | None = Field(default=None, min_length=1, max_length=2000)
    user_score: int | None = Field(default=None, ge=0, le=5)
    photos: list[ReviewPhotoInput] | None = Field(default=None, max_length=5)


class PublicSafetyZoneCreate(BaseModel):
    zone_id: int
    cctv_count: int = Field(default=0, ge=0)
    lamp_count: int = Field(default=0, ge=0)
    convenience_count: int = Field(default=0, ge=0)
    police_count: int = Field(default=0, ge=0)
    public_safety_score: float = Field(ge=0.0, le=5.0)


class SafetyScoreRequest(BaseModel):
    zone_id: int


class RoutePoint(BaseModel):
    lat: float
    lng: float


class RouteCandidate(BaseModel):
    model_config = ConfigDict(extra='allow')
    id: str
    path: list[RoutePoint]


class RouteSafetyRequest(BaseModel):
    routes: list[RouteCandidate]
