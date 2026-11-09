"""Consistent API response helpers."""

from flask import jsonify


def success(data=None, status=200, **extra):
    body = {"success": True, "data": data}
    body.update(extra)
    return jsonify(body), status


def error(code, message, status=400, details=None):
    return (
        jsonify(
            {
                "success": False,
                "error": {"code": code, "message": message, "details": details},
            }
        ),
        status,
    )
