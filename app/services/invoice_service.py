"""Printable reservation invoice rendering."""

from flask import render_template


def render_invoice(booking):
    return render_template("invoice.html", booking=booking)
