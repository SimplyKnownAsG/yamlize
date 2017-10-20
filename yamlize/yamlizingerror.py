
class YamlizingError(Exception):

    def __init__(self, msg, node=None):
        if node is not None:
            Exception.__init__(
                self, '{}\nstart: {}\nend: {}'.format(
                    msg, node.start_mark, node.end_mark))
        else:
            Exception.__init__(self, msg)
