# websitethumbnailgenerator

Small service which exposes an http API to generate thumbnails of websites using CutyCapt

Example use:

GET http://localhost:8080/?url=http://www.google.com/

Returns 503 if thumbnail is not currently available but being generated.
