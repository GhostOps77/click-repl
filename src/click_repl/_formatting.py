import typing as t
from html import escape

# from time import sleep

if t.TYPE_CHECKING:
    from typing import Union, Optional, SupportsIndex


__all__ = ["HTMLTag", "Bold", "Italics", "Underline", "StrikeThrough"]


class HTMLTag:
    name = "htmltag"

    def __init__(
        self, text: "Union[str, HTMLTag]", tag_name: "Optional[str]" = None, **attrs: str
    ) -> None:
        if isinstance(text, str):
            text = escape(text)

        self.text = text

        tag_name_extras = ""
        if tag_name is not None and " " in tag_name:
            tag_name, tag_name_extras = tag_name.split(" ", 1)
            tag_name_extras = tag_name_extras.strip()

        if tag_name_extras:
            for i in tag_name_extras.split():
                attr_info = i.split("=")

                if len(attr_info) == 1:
                    attrs[attr_info[0]] = None  # type: ignore[assignment]
                    continue

                for attr, val in attrs.items():
                    if val.startswith('"') and val.endswith('"'):
                        val = val[1:-1]
                    attrs[attr] = val

        self.tag_name = tag_name
        self.attrs = attrs

    def __str__(self) -> str:
        return self.to_formatted_text()

    def __repr__(self) -> str:
        return f"<{self.name} {self.text!r}>"
        # return str(self)

    def __len__(self) -> int:
        return len(self.text)

    def __getitem__(self, key: "Union[SupportsIndex, slice]") -> "Union[str, HTMLTag]":
        res = self.text[key]
        tag_name = self.tag_name

        if tag_name is None:
            return res

        obj = type(self)(res, **self.attrs)
        obj.tag_name = tag_name

        return obj

    def to_formatted_text(self) -> str:
        attrs_str = ""
        if self.attrs:
            attrs_str = " " + " ".join("=".join(k_v) for k_v in self.attrs.items())

        return f"<{self.tag_name}{attrs_str}>{self.text}</{self.tag_name}>"

    def get_text(self) -> str:
        text = self.text
        if isinstance(text, str):
            return text

        elif isinstance(text, HTMLTag):
            return text.get_text()

        # elif isinstance(text, FormattedString):
        #     res = []
        #     for i in text.args:
        #         if isinstance(i, str):
        #             res.append(i)

        #         elif isinstance(i, HTMLTag):
        #             res.append(i.get_text())

        #     return ''.join(res)


class Color(HTMLTag):
    def __init__(self, text: "Union[str, HTMLTag]", color: str, **attrs: str) -> None:
        super().__init__(text, color, **attrs)


class StrikeThrough(HTMLTag):
    name = "strikethrough"

    def __init__(self, text: "Union[str, HTMLTag]", **attrs: str) -> None:
        super().__init__(text, "s", **attrs)


class Bold(HTMLTag):
    name = "bold"

    def __init__(self, text: "Union[str, HTMLTag]", **attrs: str) -> None:
        super().__init__(text, "b", **attrs)


class Underline(HTMLTag):
    name = "underline"

    def __init__(self, text: "Union[str, HTMLTag]", **attrs: str) -> None:
        super().__init__(text, "u", **attrs)


class Italics(HTMLTag):
    name = "italics"

    def __init__(self, text: "Union[str, HTMLTag]", **attrs: str) -> None:
        super().__init__(text, "i", **attrs)


# class FormattedString:
#     name = "formattedstring"

#     def __init__(self, *args: "Union[str, HTMLTag]", sep: str = '') -> None:
#         self.args = args
#         self.sep = sep

#     def __str__(self) -> str:
#         return self.to_formatted_text()

#     def __repr__(self) -> str:
#         return f'<{self.name} {self.args}>'

#     def __len__(self) -> int:
#         return sum(len(i) for i in self.args)

#     def __format__(self, __format_spec: str) -> str:
#         return str(self).__format__(__format_spec)

#     def __getitem__(
#         self, key: "Union[SupportsIndex, slice]"
#     ) -> "Union[str, FormattedString]":
#         if isinstance(key, int):
#             for i in self.args:
#                 i_len = len(i)

#                 if i_len <= key:
#                     key -= i_len

#                 else:
#                     if isinstance(i, HTMLTag):
#                         return i.get_text()[key]
#                     return i[key]

#             raise IndexError("FormattedString index out of range")

#         elif isinstance(key, slice):
#             start = key.start
#             stop = key.stop

#             if key.start is None:
#                 start = 0

#             if key.stop is None:
#                 stop = len(self)

#             if key.stop < 0:
#                 stop = len(self) + key.stop

#             key = slice(start, stop)

#             if key.start > key.stop:
#                 raise ValueError(
#                     "Start value must be less than stop value"
#                     f" for slicing in {self.name}."
#                 )

#             res = []

#             for elem in self.args:
#                 if key.start >= key.stop:
#                     break

#                 val = elem[key]
#                 sliced_elem_len = len(val)

#                 if sliced_elem_len != 0:
#                     res.append(val)
#                     next_start = 0
#                     next_stop = key.stop - key.start - sliced_elem_len

#                 else:
#                     elem_len = len(elem)
#                     next_start = key.start - elem_len
#                     next_stop = key.stop - elem_len

#                 key = slice(next_start, next_stop)

#             return FormattedString(*res)

#     def get_text(self) -> str:
#         return "".join(
#             i if isinstance(i, str) else i.get_text()
#             for i in self.args
#         )

#     def to_formatted_text(self) -> str:
#         return self.sep.join(
#             i if isinstance(i, str) else str(i)
#             for i in self.args
#         )
