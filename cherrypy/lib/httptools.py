"""HTTP library functions and tools."""

# This module contains functions and tools for building an HTTP application
# framework: any one, not just one whose name starts with "Ch". ;) If you
# reference any modules from some popular framework inside *this* module,
# FuManChu will personally hang you up by your thumbs and submit you
# to a public caning.

from BaseHTTPServer import BaseHTTPRequestHandler
responseCodes = BaseHTTPRequestHandler.responses.copy()

import cgi
import re
import time
import urllib
from urlparse import urlparse


weekdayname = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
monthname = [None, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

def HTTPDate(dt=None):
    """Return the given time.struct_time as a string in RFC 1123 format.
    
    If no arguments are provided, the current time (as determined by
    time.gmtime() is used).
    
    RFC 2616: "[Concerning RFC 1123, RFC 850, asctime date formats]...
    HTTP/1.1 clients and servers that parse the date value MUST
    accept all three formats (for compatibility with HTTP/1.0),
    though they MUST only generate the RFC 1123 format for
    representing HTTP-date values in header fields."
    
    RFC 1945 (HTTP/1.0) requires the same.
    
    """
    
    if dt is None:
        dt = time.gmtime()
    
    year, month, day, hh, mm, ss, wd, y, z = dt
    # Is "%a, %d %b %Y %H:%M:%S GMT" better or worse?
    return ("%s, %02d %3s %4d %02d:%02d:%02d GMT" %
            (weekdayname[wd], day, monthname[month], year, hh, mm, ss))


class Version(object):
    
    """A version, such as "2.1 beta 3", which can be compared atom-by-atom.
    
    If a string is provided to the constructor, it will be split on word
    boundaries; that is, "1.4.13 beta 9" -> ["1", "4", "13", "beta", "9"].
    
    Comparisons are performed atom-by-atom, numerically if both atoms are
    numeric. Therefore, "2.12" is greater than "2.4", and "3.0 beta" is
    greater than "3.0 alpha" (only because "b" > "a"). If an atom is
    provided in one Version and not another, the longer Version is
    greater than the shorter, that is: "4.8 alpha" > "4.8".
    """
    
    def __init__(self, atoms):
        """A Version object. A str argument will be split on word boundaries."""
        if isinstance(atoms, basestring):
            self.atoms = re.split(r'\W', atoms)
        else:
            self.atoms = [str(x) for x in atoms]
    
    def from_http(cls, version_str):
        """Return a Version object from the given 'HTTP/x.y' string."""
        return cls(version_str[5:])
    from_http = classmethod(from_http)
    
    def to_http(self):
        """Return a 'HTTP/x.y' string for this Version object."""
        return "HTTP/%s.%s" % tuple(self.atoms[:2])
    
    def __str__(self):
        return ".".join([str(x) for x in self.atoms])
    
    def __cmp__(self, other):
        cls = self.__class__
        if not isinstance(other, cls):
            # Try to coerce other to a Version instance.
            other = cls(other)
        
        index = 0
        while index < len(self.atoms) and index < len(other.atoms):
            mine, theirs = self.atoms[index], other.atoms[index]
            if mine.isdigit() and theirs.isdigit():
                mine, theirs = int(mine), int(theirs)
            if mine < theirs:
                return -1
            if mine > theirs:
                return 1
            index += 1
        if index < len(other.atoms):
            return -1
        if index < len(self.atoms):
            return 1
        return 0


def getRanges(headervalue, content_length):
    """Return a list of (start, stop) indices from a Range header, or None.
    
    Each (start, stop) tuple will be composed of two ints, which are suitable
    for use in a slicing operation. That is, the header "Range: bytes=3-6",
    if applied against a Python string, is requesting resource[3:7]. This
    function will return the list [(3, 7)].
    """
    
    if not headervalue:
        return None
    
    result = []
    bytesunit, byteranges = headervalue.split("=", 1)
    for brange in byteranges.split(","):
        start, stop = [x.strip() for x in brange.split("-", 1)]
        if start:
            if not stop:
                stop = content_length - 1
            start, stop = map(int, (start, stop))
            if start >= content_length:
                # From rfc 2616 sec 14.16:
                # "If the server receives a request (other than one
                # including an If-Range request-header field) with an
                # unsatisfiable Range request-header field (that is,
                # all of whose byte-range-spec values have a first-byte-pos
                # value greater than the current length of the selected
                # resource), it SHOULD return a response code of 416
                # (Requested range not satisfiable)."
                continue
            if stop < start:
                # From rfc 2616 sec 14.16:
                # "If the server ignores a byte-range-spec because it
                # is syntactically invalid, the server SHOULD treat
                # the request as if the invalid Range header field
                # did not exist. (Normally, this means return a 200
                # response containing the full entity)."
                return None
            result.append((start, stop + 1))
        else:
            if not stop:
                # See rfc quote above.
                return None
            # Negative subscript (last N bytes)
            result.append((content_length - int(stop), content_length))
    
    return result


class AcceptValue(object):
    """A value (with parameters) from an Accept-* request header."""
    
    def __init__(self, value, params=None):
        self.value = value
        if params is None:
            params = {}
        self.params = params
    
    def qvalue(self):
        val = self.params.get("q", "1")
        if isinstance(val, AcceptValue):
            val = val.value
        return float(val)
    qvalue = property(qvalue, doc="The qvalue, or priority, of this value.")
    
    def __str__(self):
        p = [";%s=%s" % (k, v) for k, v in self.params.iteritems()]
        return "%s%s" % (self.value, "".join(p))
    
    def __cmp__(self, other):
        # If you sort a list of AcceptValue objects, they will be listed in
        # priority order; that is, the most preferred value will be first.
        diff = cmp(other.qvalue, self.qvalue)
        if diff == 0:
            diff = cmp(str(other), str(self))
        return diff


def getAccept(headervalue, headername='Accept'):
    """Return a list of AcceptValues from an Accept header, or None."""
    
    if not headervalue:
        return None
    
    result = []
    for capability in headervalue.split(","):
        # The first "q" parameter (if any) separates the initial
        # parameter(s) (if any) from the accept-params.
        atoms = re.split(r'; *q *=', capability, 1)
        capvalue = atoms.pop(0).strip()
        if atoms:
            qvalue = atoms[0].strip()
            if headername == 'Accept':
                # The qvalue for an Accept header can have extensions.
                atoms = [x.strip() for x in qvalue.split(";")]
                qvalue = atoms.pop(0).strip()
                ext = {}
                for atom in atoms:
                    atom = atom.split("=", 1)
                    key = atom.pop(0).strip()
                    if atom:
                        val = atom[0].strip()
                    else:
                        val = ""
                    ext[key] = val
                qvalue = AcceptValue(qvalue, ext)
            params = {"q": qvalue}
        else:
            params = {}
        
        if headername == 'Accept':
            # The media-range may have parameters (before the qvalue).
            atoms = [x.strip() for x in capvalue.split(";")]
            capvalue = atoms.pop(0).strip()
            for atom in atoms:
                atom = atom.split("=", 1)
                key = atom.pop(0).strip()
                if atom:
                    val = atom[0].strip()
                else:
                    val = ""
                params[key] = val
        
        result.append(AcceptValue(capvalue, params))
    
    result.sort()
    return result


def validStatus(status):
    """Return legal HTTP status Code, Reason-phrase and Message.
    
    The status arg must be an int, or a str that begins with an int.
    
    If status is an int, or a str and  no reason-phrase is supplied,
    a default reason-phrase will be provided.
    """
    
    if not status:
        status = 200
    
    status = str(status)
    parts = status.split(" ", 1)
    if len(parts) == 1:
        # No reason supplied.
        code, = parts
        reason = None
    else:
        code, reason = parts
        reason = reason.strip()
    
    try:
        code = int(code)
    except ValueError:
        raise ValueError("Illegal response status from server (non-numeric).")
    
    if code < 100 or code > 599:
        raise ValueError("Illegal response status from server (out of range).")
    
    if code not in responseCodes:
        # code is unknown but not illegal
        defaultReason, message = "", ""
    else:
        defaultReason, message = responseCodes[code]
    
    if reason is None:
        reason = defaultReason
    
    return code, reason, message

def parseRequestLine(requestLine):
    """Return (method, path, querystring, protocol) from a requestLine."""
    method, path, protocol = requestLine.split()
    
    # path may be an abs_path (including "http://host.domain.tld");
    # Ignore scheme, location, and fragments (so config lookups work).
    # [Therefore, this assumes all hosts are valid for this server.]
    scheme, location, path, params, qs, frag = urlparse(path)
    if path == "*":
        # "...the request does not apply to a particular resource,
        # but to the server itself". See
        # http://www.w3.org/Protocols/rfc2616/rfc2616-sec5.html#sec5.1.2
        pass
    else:
        if params:
            params = ";" + params
        path = path + params
        
        # Unquote the path (e.g. "/this%20path" -> "this path").
        # http://www.w3.org/Protocols/rfc2616/rfc2616-sec5.html#sec5.1.2
        # Note that cgi.parse_qs will decode the querystring for us.
        path = urllib.unquote(path)
    
    return method, path, qs, protocol

def parseQueryString(queryString, keep_blank_values=True):
    """Build a paramMap dictionary from a queryString."""
    if re.match(r"[0-9]+,[0-9]+", queryString):
        # Server-side image map. Map the coords to 'x' and 'y'
        # (like CGI::Request does).
        pm = queryString.split(",")
        pm = {'x': int(pm[0]), 'y': int(pm[1])}
    else:
        pm = cgi.parse_qs(queryString, keep_blank_values)
        for key, val in pm.items():
            if len(val) == 1:
                pm[key] = val[0]
    return pm

def paramsFromCGIForm(form):
    paramMap = {}
    for key in form.keys():
        valueList = form[key]
        if isinstance(valueList, list):
            paramMap[key] = []
            for item in valueList:
                if item.filename is not None:
                    value = item # It's a file upload
                else:
                    value = item.value # It's a regular field
                paramMap[key].append(value)
        else:
            if valueList.filename is not None:
                value = valueList # It's a file upload
            else:
                value = valueList.value # It's a regular field
            paramMap[key] = value
    return paramMap


class HeaderMap(dict):
    """A dict subclass for HTTP request and response headers.
    
    Each key is changed on entry to str(key).title(). This allows headers
    to be case-insensitive and avoid duplicates.
    """
    
    def __getitem__(self, key):
        return dict.__getitem__(self, str(key).title())
    
    def __setitem__(self, key, value):
        dict.__setitem__(self, str(key).title(), value)
    
    def __delitem__(self, key):
        dict.__delitem__(self, str(key).title())
    
    def __contains__(self, item):
        return dict.__contains__(self, str(item).title())
    
    def get(self, key, default=None):
        return dict.get(self, str(key).title(), default)
    
    def has_key(self, key):
        return dict.has_key(self, str(key).title())
    
    def update(self, E):
        for k in E.keys():
            self[str(k).title()] = E[k]
    
    def fromkeys(cls, seq, value=None):
        newdict = cls()
        for k in seq:
            newdict[str(k).title()] = value
        return newdict
    fromkeys = classmethod(fromkeys)
    
    def setdefault(self, key, x=None):
        key = str(key).title()
        try:
            return self[key]
        except KeyError:
            self[key] = x
            return x
    
    def pop(self, key, default):
        return dict.pop(self, str(key).title(), default)
