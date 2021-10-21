Module zenml.cli.utils
======================

Functions
---------

    
`confirmation(text: str, *args, **kwargs) ‑> bool`
:   Echo a confirmation string on the CLI.
    
    Args:
      text: Input text string.
      *args: Args to be passed to click.confirm().
      **kwargs: Kwargs to be passed to click.confirm().
    
    Returns:
        Boolean based on user response.

    
`declare(text: str)`
:   Echo a declaration on the CLI.
    
    Args:
      text: Input text string.

    
`echo_component_list(component_list: Dict[str, zenml.core.base_component.BaseComponent])`
:   Echoes a list of components in a pretty style.

    
`error(text: str)`
:   Echo an error string on the CLI.
    
    Args:
      text: Input text string.
    
    Raises:
        click.ClickException when called.

    
`format_date(dt: datetime.datetime, format: str = '%Y-%m-%d %H:%M:%S') ‑> str`
:   Format a date into a string.
    
    Args:
      dt: Datetime object to be formatted.
      format: The format in string you want the datetime formatted to.
    
    Returns:
        Formatted string according to specification.

    
`format_timedelta(td: datetime.timedelta) ‑> str`
:   Format a timedelta into a string.
    
    Args:
      td: datetime.timedelta object to be formatted.
    
    Returns:
        Formatted string according to specification.

    
`notice(text: str)`
:   Echo a notice string on the CLI.
    
    Args:
      text: Input text string.

    
`parse_unknown_options(args: List[str]) ‑> Dict[str, Any]`
:   Parse unknown options from the cli.
    
    Args:
      args: A list of strings from the CLI.
    
    Returns:
        Dict of parsed args.

    
`pretty_print(obj: Any)`
:   Pretty print an object on the CLI.
    
    Args:
      obj: Any object with a __str__ method defined.

    
`question(text: str, *args, **kwargs) ‑> Any`
:   Echo a question string on the CLI.
    
    Args:
      text: Input text string.
      *args: Args to be passed to click.prompt().
      **kwargs: Kwargs to be passed to click.prompt().
    
    Returns:
        The answer to the question of any type, usually string.

    
`title(text: str)`
:   Echo a title formatted string on the CLI.
    
    Args:
      text: Input text string.

    
`warning(text: str)`
:   Echo a warning string on the CLI.
    
    Args:
      text: Input text string.