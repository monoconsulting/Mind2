Swea API

v1

API definition
Changelog
SWEA API for interest rates and exchange rates

See our FAQ for more information of how to use the API.

Disclaimer
The exchange rates are indicative only and are published by the Riksbank for information purposes. They should therefore not be used for transactional purposes.
Reservation
The Riksbank disclaims liability for any errors or changes in values afterwards and for any interruptions in the functioning of the website and the API:s that may affect access to the statistics.
The Riksbank reserves the right to make updates/changes to the website and the API:s that may affect the downloading of statistics.
More information on the Riksbank's website.

CalendarDays
Try it 
Swedish banking day(s) starting with {from} ending with today.

CalendarDays
Request
https://api.riksbank.se/swea/v1/CalendarDays/{from}
Request parameters
Name
In
Required
Type
Description
from
template
true
string
Format - date-time (as date-time in RFC3339). ISO 8601 date (YYYY-MM-DD).

Response: 200 OK
OK


application/json
CalendarDays-from-Get200ApplicationJsonResponse


Name
Required
Type
Description
[]
true
CalendarDay[]
default
default - json
 Copy
[{
    "calendarDate": "string",
    "swedishBankday": true,
    "weekYear": 0,
    "weekNumber": 0,
    "quarterNumber": 0,
    "ultimo": true
}]
Response: 204 No Content
No Content


Response: 400 Bad Request
Bad Request


application/json
ProblemDetails


Name
Required
Type
Description
type
false
string
title
false
string
status
false
integer (int32)
detail
false
string
instance
false
string
default
default - json
 Copy
{
    "type": "string",
    "title": "string",
    "status": 0,
    "detail": "string",
    "instance": "string"
}
Response: 500 Internal Server Error
Internal Server Error


Definitions
Name
Description
CalendarDay
ProblemDetails
CalendarDays-from-Get200ApplicationJsonResponse
CalendarDay


Name
Required
Type
Description
calendarDate
true
string
The date of the day in ISO 8601 format YYYY-MM-DD.

swedishBankday
true
boolean
Is true if the Calendar Date is a Swedish bank day.

weekYear
true
integer (int32)
The year the WeekNumber belongs to.

weekNumber
true
integer (int32)
The week of the year according to the ISO 8601 standard.

quarterNumber
true
integer (int32)
The quarter of the year.

ultimo
true
boolean
True if the Calendar day is the last bankday in the month.

ProblemDetails


Name
Required
Type
Description
type
false
string
title
false
string
status
false
integer (int32)
detail
false
string
instance
false
string
CalendarDays-from-Get200ApplicationJsonResponse


Name
Required
Type
Description
[]
true
CalendarDay[]
