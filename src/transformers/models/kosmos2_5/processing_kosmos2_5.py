# coding=utf-8
# Copyright 2023 The HuggingFace Inc. team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Processor class for Kosmos2_5.
bf16 now
"""

from typing import List, Optional, Union

from ...image_processing_utils import BatchFeature
from ...image_utils import ImageInput, is_batched
from ...processing_utils import ProcessorMixin
from ...tokenization_utils_base import BatchEncoding, PaddingStrategy, PreTokenizedInput, TextInput, TruncationStrategy
from ...utils import TensorType
import torch


class Kosmos2_5Processor(ProcessorMixin):
    r"""
    Constructs a Kosmos2_5 processor which wraps a BERT tokenizer and Kosmos2_5 image processor into a single
    processor.

    [`Kosmos2_5Processor`] offers all the functionalities of [`Kosmos2_5ImageProcessor`] and [`T5TokenizerFast`]. See
    the docstring of [`~Kosmos2_5Processor.__call__`] and [`~Kosmos2_5Processor.decode`] for more information.

    Args:
        image_processor (`Kosmos2_5ImageProcessor`):
            An instance of [`Kosmos2_5ImageProcessor`]. The image processor is a required input.
        tokenizer (Union[`T5TokenizerFast`, `T5Tokenizer`]):
            An instance of ['T5TokenizerFast`] or ['T5Tokenizer`]. The tokenizer is a required input.
    """

    attributes = ["image_processor", "tokenizer"]
    image_processor_class = "Kosmos2_5ImageProcessor"
    tokenizer_class = "PreTrainedTokenizerFast"

    def __init__(self, image_processor, tokenizer):
        tokenizer.return_token_type_ids = False
        super().__init__(image_processor, tokenizer)

    def __call__(
        self,
        images=None,
        text: Union[TextInput, List[TextInput]] = None,
        add_special_tokens: bool = True,
        padding: Union[bool, str, PaddingStrategy] = True,
        truncation: Union[bool, str, TruncationStrategy] = True,
        max_length: Optional[int] = None,
        max_patches: Optional[int] = 4096,
        stride: int = 0,
        pad_to_multiple_of: Optional[int] = None,
        return_attention_mask: Optional[bool] = None,
        return_tensors: Optional[Union[str, TensorType]] = "pt",
        **kwargs,
    ) -> BatchFeature:
        """
        This method uses [`Kosmos2_5ImageProcessor.preprocess`] method to prepare image(s) for the model, and
        [`PreTrainedTokenizerFast.__call__`] to prepare text for the model.

        Please refer to the docstring of the above two methods for more information.

        The rest of this documentation shows the arguments specific to `Kosmos2_5Processor`.
        """
        if images is None and text is None:
            raise ValueError("You have to specify either images or text.")

        encoding = BatchFeature()

        if images is not None:
            image_encoding = self.image_processor(
                images, return_tensors=return_tensors, max_patches=max_patches, **kwargs
            )
            image_encoding.pop("rows")
            image_encoding.pop("cols")
            encoding.update(image_encoding)

        if text is not None:
            # use updates or pop
            input = self.tokenizer(text, 
                                        add_special_tokens=add_special_tokens,
                                        padding=padding,
                                        truncation=truncation,
                                        max_length=max_length,
                                        stride=stride,
                                        pad_to_multiple_of=pad_to_multiple_of,
                                        return_attention_mask=return_attention_mask,
                                        return_tensors="pt")

            batch_size, seq_len = input.input_ids.shape
            additional_tokens = [0, 100283] + [0] * 2048 + [100284]
            additional_tokens_tensor = torch.tensor(additional_tokens).unsqueeze(0).repeat(batch_size, 1)
            input_ids = torch.cat([additional_tokens_tensor, input.input_ids], dim=1)

            image_embeds_position_mask = [0, -1] + [1] * 2048 + [-1] + [0] * seq_len
            image_embeds_position_mask = torch.LongTensor(image_embeds_position_mask).unsqueeze(0).repeat(batch_size, 1)

            added_attention_mask = [1, 1] + [1]*2048 + [1]
            added_attention_mask_tensor = torch.tensor(added_attention_mask).unsqueeze(0).repeat(batch_size, 1)
            attention_mask = torch.cat([added_attention_mask_tensor, input.attention_mask], dim=1)
            encoding.update({"input_ids": input_ids, "attention_mask": attention_mask, "image_embeds_position_mask": image_embeds_position_mask})

        return encoding

    def batch_decode(self, *args, **kwargs):
        """
        This method forwards all its arguments to Kosmos2_5TokenizerFast's [`~PreTrainedTokenizer.batch_decode`].
        Please refer to the docstring of this method for more information.
        """
        return self.tokenizer.batch_decode(*args, **kwargs)

    def decode(self, *args, **kwargs):
        """
        This method forwards all its arguments to Kosmos2_5TokenizerFast's [`~PreTrainedTokenizer.decode`]. Please
        refer to the docstring of this method for more information.
        """
        return self.tokenizer.decode(*args, **kwargs)

    @property
    def model_input_names(self):
        tokenizer_input_names = self.tokenizer.model_input_names
        image_processor_input_names = self.image_processor.model_input_names
        return list(dict.fromkeys(tokenizer_input_names + image_processor_input_names))
