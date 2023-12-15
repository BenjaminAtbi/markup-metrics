from pathlib import Path
from typing import List
import pyter
import difflib
import yaml

from metric_engines.types import MetricInput


class MetricEngine:
    unit = "%"

    def stripXML(self, hypothesis_tokens: List[str]) -> List[str]:
        if len(hypothesis_tokens) == 0: return hypothesis_tokens
        if hypothesis_tokens[0].startswith('<') and hypothesis_tokens[-1].endswith('>'):
            merged_tokens = ''.join(hypothesis_tokens)
            index_after_open_tag = merged_tokens.find('>') + 1
            rev_index_before_close_tag = merged_tokens[::-1].find('<') + 1
            #return unstripped response if it doesn't fit the pattern
            if index_after_open_tag > len(merged_tokens) - rev_index_before_close_tag: return hypothesis_tokens

            for token_index, token in enumerate(hypothesis_tokens):
                if len(token) <= index_after_open_tag:
                    index_after_open_tag -= len(token)
                else:
                    token = token[index_after_open_tag:]
                    first_token = token_index
                    break
            for token_index, token in reversed(list(enumerate(hypothesis_tokens))):
                if len(token) > rev_index_before_close_tag:
                    rev_index_before_close_tag -= len(token)
                else:
                    token = token[:-rev_index_before_close_tag]
                    last_token = token_index
                    break
            return hypothesis_tokens[first_token:last_token]
        return hypothesis_tokens

    def calculate(self, input: MetricInput, output_file_dir: Path) -> float:

        stripped_hypothesis_tokens = self.stripXML(input.hypothesis_tokens)
        stripped_reference_tokens = self.stripXML(input.reference_tokens)

        with input.profile_logger.log_time("xater.difflib"):
            diffs = difflib.unified_diff(
                stripped_reference_tokens,
                stripped_hypothesis_tokens,
                tofile="reference",
                fromfile="hypothesis",
            )
        (output_file_dir / "hypothesis_tokenized.txt").write_text(
            "\n".join(stripped_hypothesis_tokens)
        )
        (output_file_dir / "referenced_tokenized.txt").write_text(
            "\n".join(stripped_reference_tokens)
        )
        cdiff = "\n".join(diffs)
        output_file_path = output_file_dir / "unified_diff.txt"
        output_file_path.write_text(cdiff)
        output_report = output_file_dir / "report.yml"
        with input.profile_logger.log_time("xater.pyter"):
            ter = pyter.ter(stripped_hypothesis_tokens, stripped_reference_tokens)
            clamped_ter = clamp(ter, 0, 1)
            score = 100 - clamped_ter * 100

        output_report.write_text(
            yaml.dump(
                {
                    "input_file": str(input.input_file.absolute()),
                    "input_text": input.input_text,
                    "reference_text": input.reference_text,
                    "hypothesis_text": input.hypothesis_text,
                }
            )
        )

        return score


def clamp(number, bottom, top):
    return max(bottom, min(number, top))
