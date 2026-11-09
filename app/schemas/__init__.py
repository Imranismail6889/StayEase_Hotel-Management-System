"""Marshmallow request schemas."""

from marshmallow import Schema, fields, validate


class RegisterSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=2, max=120))
    email = fields.Email(required=True)
    phone = fields.Str(load_default="", validate=validate.Length(max=40))
    password = fields.Str(required=True, validate=validate.Length(min=8, max=128))


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=1, max=128))


class ProfileSchema(Schema):
    name = fields.Str(validate=validate.Length(min=2, max=120))
    phone = fields.Str(validate=validate.Length(max=40))


class PasswordSchema(Schema):
    current_password = fields.Str(required=True)
    new_password = fields.Str(required=True, validate=validate.Length(min=8, max=128))


class EmailSchema(Schema):
    email = fields.Email(required=True)


class RoomQuerySchema(Schema):
    type = fields.Str(load_default="")
    status = fields.Str(load_default="")
    min_price = fields.Decimal(as_string=True, load_default=None)
    max_price = fields.Decimal(as_string=True, load_default=None)
    capacity = fields.Int(load_default=None, validate=validate.Range(min=1, max=20))
    amenities = fields.Str(load_default="")
    check_in = fields.Date(load_default=None)
    check_out = fields.Date(load_default=None)
    sort = fields.Str(load_default="")
    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Int(load_default=12, validate=validate.Range(min=1, max=100))


class DateRangeSchema(Schema):
    from_date = fields.Date(data_key="from", required=True)
    to_date = fields.Date(data_key="to", required=True)


class QuoteSchema(Schema):
    room_id = fields.Int(required=True, validate=validate.Range(min=1))
    check_in = fields.Date(required=True)
    check_out = fields.Date(required=True)
    guests = fields.Int(load_default=1, validate=validate.Range(min=1, max=20))
    extras = fields.List(fields.Str(), load_default=list)
    promo_code = fields.Str(load_default="", validate=validate.Length(max=40))


class BookingSchema(QuoteSchema):
    method = fields.Str(
        load_default="credit_card",
        validate=validate.OneOf(["credit_card", "debit_card", "upi", "net_banking"]),
    )
    card_last4 = fields.Str(load_default="", validate=validate.Regexp(r"^$|^\d{4}$"))
    card_brand = fields.Str(load_default="", validate=validate.Length(max=24))
    special_requests = fields.Str(load_default="", validate=validate.Length(max=1000))


class ModifyBookingSchema(Schema):
    check_in = fields.Date(required=True)
    check_out = fields.Date(required=True)
    guests = fields.Int(load_default=None, validate=validate.Range(min=1, max=20))


class ReviewSchema(Schema):
    booking_id = fields.Int(required=True)
    rating = fields.Int(required=True, validate=validate.Range(min=1, max=5))
    comment = fields.Str(load_default="", validate=validate.Length(max=2000))


class FavoriteSchema(Schema):
    room_id = fields.Int(required=True)


class PromoValidateSchema(Schema):
    code = fields.Str(required=True, validate=validate.Length(min=2, max=40))
    nights = fields.Int(required=True, validate=validate.Range(min=1, max=365))


class NewsletterSchema(EmailSchema):
    pass


class RoomWriteSchema(Schema):
    room_number = fields.Str(required=True, validate=validate.Length(min=1, max=20))
    name = fields.Str(required=True, validate=validate.Length(min=2, max=120))
    room_type = fields.Str(
        required=True, validate=validate.OneOf(["Standard", "Deluxe", "Suite"])
    )
    description = fields.Str(load_default="", validate=validate.Length(max=1200))
    price_per_night = fields.Decimal(
        required=True, as_string=True, validate=validate.Range(min=0)
    )
    capacity = fields.Int(required=True, validate=validate.Range(min=1, max=20))
    floor = fields.Int(load_default=1, validate=validate.Range(min=0, max=100))
    status = fields.Str(
        load_default="available",
        validate=validate.OneOf(["available", "occupied", "maintenance"]),
    )
    image_urls = fields.List(fields.Str(), load_default=list)
    amenities = fields.List(fields.Str(), load_default=list)


class RoomStatusSchema(Schema):
    status = fields.Str(
        required=True, validate=validate.OneOf(["available", "occupied", "maintenance"])
    )


class BookingStatusSchema(Schema):
    status = fields.Str(
        required=True,
        validate=validate.OneOf(
            ["confirmed", "checked_in", "checked_out", "cancelled"]
        ),
    )


class PromoWriteSchema(Schema):
    code = fields.Str(required=True, validate=validate.Length(min=2, max=40))
    discount_percent = fields.Decimal(
        required=True, as_string=True, validate=validate.Range(min=0, max=100)
    )
    min_nights = fields.Int(load_default=1, validate=validate.Range(min=1))
    valid_to = fields.DateTime(required=True)
    max_uses = fields.Int(load_default=1000, validate=validate.Range(min=1))
    is_active = fields.Bool(load_default=True)


class SettingSchema(Schema):
    settings = fields.Dict(keys=fields.Str(), values=fields.Str(), required=True)


class PaginationSchema(Schema):
    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Int(load_default=20, validate=validate.Range(min=1, max=100))
    search = fields.Str(load_default="", validate=validate.Length(max=120))
    status = fields.Str(load_default="")
    from_date = fields.Date(data_key="from", load_default=None)
    to_date = fields.Date(data_key="to", load_default=None)
