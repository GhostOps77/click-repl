# from prompt_toolkit.validation import Validator, ValidationError
# from ._parser import _split_args


# class ClickValidator(Validator):
#     def validate(self, document):
#         tmp = _split_args(document.text_before_cursor)

#         if tmp is None:
#             return

#         args, incomplete = tmp
#         i = 0

#         raise ValidationError(
#             message='This input contains non-numeric characters', cursor_position=i
#         )
