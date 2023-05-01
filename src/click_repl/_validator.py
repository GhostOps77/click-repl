# from prompt_toolkit.validation import Validator, ValidationError
# from ._parser import _split_args


# class ClickValidator(Validator):
#     def validate(self, document):
#         if document.text.startswith(
#             (self.internal_cmd_prefix, self.system_cmd_prefix)
#         ):
#             return

#         args, incomplete = _split_args(document.text_before_cursor)

#         i = 0

#         raise ValidationError(
#             message='This input contains non-numeric characters', cursor_position=i
#         )
