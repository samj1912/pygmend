from typing import List
from pydocstyle.parser import Function

import re
import textwrap
import nltk
from collections import namedtuple
from pydocstyle.utils import pairwise

nltk.download("punkt")
SENT_TOKENIZER = nltk.data.load("tokenizers/punkt/english.pickle")
LEADING_SPACE = re.compile(r"^(\s+)")
LEADING_WORD = re.compile("(\w+)")
TAB_SIZE = 4

GOOGLE_SECTION_NAMES = (
    "Args",
    "Arguments",
    "Attention",
    "Attributes",
    "Caution",
    "Danger",
    "Error",
    "Example",
    "Examples",
    "Hint",
    "Important",
    "Keyword Args",
    "Keyword Arguments",
    "Methods",
    "Note",
    "Notes",
    "Other Parameters",
    "Parameters",
    "Return",
    "Returns",
    "Raises",
    "References",
    "See Also",
    "Tip",
    "Todo",
    "Warning",
    "Warnings",
    "Warns",
    "Yield",
    "Yields",
)


def get_leading_words(line):
    """Return any leading set of words from `line`.
    For example, if `line` is "  Hello world!!!", returns "Hello world".
    """
    match = LEADING_WORD.match(line.strip())
    if match is not None:
        return match.group()


def get_leading_space(line: str) -> int:
    line = line.replace("\t", " " * TAB_SIZE)
    match = LEADING_SPACE.match(line)
    if match:
        return len(match.group(1))
    return 0


def fix_function(definition: Function, line_length=79):
    docstring: str = definition.docstring
    start_indent = get_leading_space(definition.source) + TAB_SIZE
    docstring = docstring[3:-3].strip()
    lines = docstring.splitlines()
    summary, *_ = SENT_TOKENIZER.tokenize(lines[0])
    if len(summary) > line_length - 1:
        shortened_summary = summary[: line_length - 3]
        shortened_summary += "..."
        rest_of_summary = "..." + summary[line_length - 3 :].strip()
    else:
        if not summary.endswith(("?", ".", "!")):
            shortened_summary = summary + "."
        else:
            shortened_summary = summary
        rest_of_summary = ""
    shortened_summary = shortened_summary.capitalize()
    rest = rest_of_summary + "\n" + docstring[len(lines[0]) :]
    if rest.strip():
        sections = split_sections(rest.strip())
    else:
        sections = {}
    formatters = {"args": format_general_section, "description": format_description}
    no_format = {"example", "examples"}
    output_sections = []
    for section, content in sections.items():
        if section.lower() in no_format:
            content = format_exception(content, start_indent)
        else:
            formatter = formatters.get(section.lower(), format_general_section)
            content = formatter(section, content, start_indent, line_length)
        if section != "Description":
            section_content = "{indent}{section}:\n{content}".format(
                indent=" " * start_indent, section=section, content=content
            )
        else:
            section_content = content.capitalize()
        output_sections.append(section_content)
    print(
        "{indent}{summary}".format(indent=" " * start_indent, summary=shortened_summary)
    )
    print("")
    for section in output_sections:
        print(section)
        print("")
    return (1, [])


def format_description(_, content, start_indent, line_length):
    indent = " " * (start_indent)
    wrapper = textwrap.TextWrapper(
        width=line_length, initial_indent=indent, subsequent_indent=indent
    )
    return "\n".join(wrapper.wrap(content)).capitalize()


def format_general_section(section, content, start_indent, line_length):
    indent = " " * (start_indent + TAB_SIZE)
    wrapper = textwrap.TextWrapper(
        width=line_length, initial_indent=indent, subsequent_indent=indent
    )
    return "\n".join(wrapper.wrap(content))


def format_exception(content, start_indent):
    output = []
    indent = " " * (start_indent + TAB_SIZE)
    for line in content.splitlines():
        line = line.strip()
        line = f"{indent}{line}"
        output.append(line)
    return "\n".join(output)


def split_sections(docstring):
    lines = docstring.splitlines()
    lines = list(map(str.strip, lines))
    lower_section_names = [s.lower() for s in GOOGLE_SECTION_NAMES]

    def _suspected_as_section(_line):
        result = get_leading_words(_line.lower())
        return result in lower_section_names

    # Finding our suspects.
    suspected_section_indices = [
        i for i, line in enumerate(lines) if _suspected_as_section(line)
    ]

    SectionContext = namedtuple(
        "SectionContext",
        (
            "section_name",
            "previous_line",
            "line",
            "following_lines",
            "original_index",
            "is_last_section",
        ),
    )

    # First - create a list of possible contexts. Note that the
    # `following_lines` member is until the end of the docstring.
    contexts = (
        SectionContext(
            get_leading_words(lines[i].strip()),
            lines[i - 1] if i > 0 else "",
            lines[i],
            lines[i + 1 :],
            i,
            False,
        )
        for i in suspected_section_indices
    )

    # Now that we have manageable objects - rule out false positives.
    contexts = [c for c in contexts if is_docstring_section(c)]
    if not contexts:
        description_end = None
    else:
        description_end = contexts[0].original_index
    if description_end != 0:
        contexts = [
            SectionContext(
                "Description", "", lines[0], lines[1:description_end], -1, False
            )
        ] + contexts

    # Now we shall trim the `following lines` field to only reach the
    # next section name.
    sections = {}
    for a, b in pairwise(contexts, None):
        end = b and b.original_index
        content = "\n".join(map(str.strip, lines[a.original_index + 1 : end]))
        if content:
            sections[a.section_name.capitalize()] = content
    return sections


def is_blank(string: str) -> bool:
    """Return True iff the string contains only whitespaces."""
    return not string.strip()


def is_docstring_section(context):
    """Check if the suspected context is really a section header.
    Lets have a look at the following example docstring:
        '''Title.
        Some part of the docstring that specifies what the function
        returns. <----- Not a real section name. It has a suffix and the
                        previous line is not empty and does not end with
                        a punctuation sign.
        This is another line in the docstring. It describes stuff,
        but we forgot to add a blank line between it and the section name.
        Parameters:  <-- A real section name. The previous line ends with
                        a period, therefore it is in a new
                        grammatical context and it ends with a colon.
        param : int
        examples : list  <------- Not a section - previous line doesn't end
            A list of examples.   with punctuation.
        notes : list  <---------- Not a section - there's text after the
            A list of notes.      colon.
        Notes  <--- Suspected as a context because there's no colon,
                    so probably a mistake.
        Bla.
        '''
    To make sure this is really a section we check these conditions:
        * There's no suffix to the section name or it's just a colon AND
        * The previous line is empty OR it ends with punctuation.

    """
    section_name_suffix = (
        context.line.strip().lstrip(context.section_name.strip()).strip()
    )

    section_suffix_is_only_colon = section_name_suffix == ":"

    punctuation = [",", ";", ".", "-", "\\", "/", "]", "}", ")"]
    prev_line_ends_with_punctuation = any(
        context.previous_line.strip().endswith(x) for x in punctuation
    )

    this_line_looks_like_a_section_name = (
        is_blank(section_name_suffix) or section_suffix_is_only_colon
    )

    prev_line_looks_like_end_of_paragraph = prev_line_ends_with_punctuation or is_blank(
        context.previous_line
    )

    return this_line_looks_like_a_section_name and prev_line_looks_like_end_of_paragraph


"""
Docstring:
    Title:
        Top line: Long - segment - continuation
    Description:
        continuation
        blank line
    Args:
        name (type): Description

"""
