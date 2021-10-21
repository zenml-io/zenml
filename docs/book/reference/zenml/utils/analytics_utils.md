Module zenml.utils.analytics_utils
==================================
Analytics code for ZenML

Functions
---------

    
`get_segment_key() ‑> str`
:   Get key for authorizing to Segment backend.
    
    Returns:
        Segment key as a string.
    
    Raises:
        requests.exceptions.RequestException if request times out.

    
`get_system_info() ‑> Dict`
:   Returns system info as a dict.
    
    Returns:
        A dict of system information.

    
`in_docker()`
:   Returns: True if running in a Docker container, else False

    
`initialize_telemetry()`
:   Initializes telemetry with the right key

    
`parametrized(dec)`
:   This is a meta-decorator, that is, a decorator for decorators.
    As a decorator is a function, it actually works as a regular decorator
    with arguments:

    
`track(*args: Any, **kwargs: Any)`
:   Internal layer

    
`track_event(event: str, metadata: Dict = None)`
:   Track segment event if user opted-in.
    
    Args:
        event: Name of event to track in segment.
        metadata: Dict of metadata to track.