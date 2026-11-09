"""Calendar event export."""


def make_ics(booking):
    ref = booking.booking_ref
    room_name = booking.room.name.replace(",", r"\,").replace(";", r"\;")
    return "\r\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//StayEase//Hotel//EN",
            "BEGIN:VEVENT",
            "UID:" + ref + "@stayease.com",
            "DTSTAMP:" + booking.created_at.strftime("%Y%m%dT%H%M%SZ"),
            "DTSTART;VALUE=DATE:" + booking.check_in_date.strftime("%Y%m%d"),
            "DTEND;VALUE=DATE:" + booking.check_out_date.strftime("%Y%m%d"),
            "SUMMARY:StayEase - " + room_name,
            "DESCRIPTION:Reservation " + ref,
            "END:VEVENT",
            "END:VCALENDAR",
            "",
        ]
    )
