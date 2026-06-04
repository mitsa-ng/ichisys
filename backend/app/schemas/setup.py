from pydantic import BaseModel, field_validator


class SetupAdminRequest(BaseModel):
    email: str
    password: str
    display_name: str

    @field_validator("email")
    @classmethod
    def email_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Email is required")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v

    @field_validator("display_name")
    @classmethod
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Display name is required")
        return v.strip()
