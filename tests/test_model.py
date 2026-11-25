from nlp.model import LocalT5Rewriter


class TokenizerStub:
    def __init__(self):
        self.seen = None

    def encode(self, text, add_special_tokens):
        self.seen = text
        assert add_special_tokens is True
        return text.split()


class ModelStub:
    def eval(self):
        pass


def test_token_count_includes_local_model_prompt_prefix():
    tokenizer = TokenizerStub()
    rewriter = LocalT5Rewriter(tokenizer, ModelStub(), prompt_prefix="grammar:")
    assert rewriter.count_tokens("The cell is.") == 4
    assert tokenizer.seen == "grammar: The cell is."
