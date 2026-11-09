"""Customer saved rooms."""

from flask import Blueprint, g
from app.extensions import db
from app.models import Favorite, Room
from app.schemas import FavoriteSchema
from app.utils.decorators import authenticated, validate_with
from app.utils.errors import APIError
from app.utils.responses import success

bp = Blueprint("favorites", __name__, url_prefix="/api/favorites")


@bp.get("")
@authenticated
def list_favorites():
    favorites = Favorite.query.filter_by(user_id=g.current_user.id).all()
    return success([item.room.to_dict() for item in favorites if item.room])


@bp.post("")
@authenticated
@validate_with(FavoriteSchema)
def add_favorite():
    room = db.session.get(Room, g.validated["room_id"])
    if not room:
        raise APIError("not_found", "Room not found.", 404)
    favorite = db.session.get(Favorite, (g.current_user.id, room.id))
    if not favorite:
        db.session.add(Favorite(user_id=g.current_user.id, room_id=room.id))
        db.session.commit()
    return success(room.to_dict(), 201)


@bp.delete("/<int:room_id>")
@authenticated
def remove_favorite(room_id):
    favorite = db.session.get(Favorite, (g.current_user.id, room_id))
    if favorite:
        db.session.delete(favorite)
        db.session.commit()
    return success({"removed": True})
