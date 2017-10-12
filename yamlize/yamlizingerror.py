
class YamlizingError(Exception):

    def __init__(self, msg, node):
        Exception.__init__(self, '{}\nstart: {}\nend: {}'.format(msg, node.start_mark, node.end_mark))


