"""
OCR Service using OCR.space Free API
No credit card required - 25,000 requests/month free
"""

import requests
import os
import logging
from typing import List, Dict
from PIL import Image, ImageEnhance
import io

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 1024 * 1024  # 1024 KB — OCR.space free tier limit


class OCRService:
    """
    Service for extracting text from images using OCR.space Free API
    Free tier: 25,000 requests/month, no credit card required
    """

    def __init__(self):
        """
        Initialize OCR.space API client
        Get free API key from: https://ocr.space/ocrapi
        """
        # Default free API key (limited but works)
        # Get your own free key from: https://ocr.space/ocrapi
        self.api_key = os.environ.get('OCRSPACE_API_KEY', 'helloworld')
        self.api_url = 'https://api.ocr.space/parse/image'

        logger.info("OCR.space API initialized - 25,000 free requests/month")

    def compress_image_under_limit(self, img: Image.Image, max_bytes: int = MAX_FILE_SIZE_BYTES) -> bytes:
        """
        Compress a PIL image to JPEG bytes under max_bytes.
        Tries decreasing quality first, then downscales if needed.

        Args:
            img: PIL Image (RGB)
            max_bytes: Maximum allowed size in bytes

        Returns:
            Compressed image bytes (JPEG)
        """
        # Try JPEG compression at decreasing quality levels
        for quality in [95, 85, 75, 65, 55, 45, 35]:
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=quality, optimize=True)
            data = buf.getvalue()
            if len(data) <= max_bytes:
                logger.debug(f"Compressed to {len(data) / 1024:.1f} KB at quality={quality}")
                return data

        # If still too large, downscale progressively and re-compress
        scale = 0.9
        while scale >= 0.2:
            width, height = img.size
            new_size = (int(width * scale), int(height * scale))
            resized = img.resize(new_size, Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            resized.save(buf, format='JPEG', quality=55, optimize=True)
            data = buf.getvalue()
            if len(data) <= max_bytes:
                logger.debug(f"Compressed to {len(data) / 1024:.1f} KB at scale={scale:.1f}")
                return data
            scale -= 0.1

        # Last resort — return whatever we have at smallest scale
        logger.warning("Could not compress image under limit; sending smallest possible version")
        return data

    def preprocess_image_basic(self, image_path: str) -> bytes:
        """
        Basic image preprocessing to improve OCR accuracy,
        while ensuring the output stays under OCR.space's 1024 KB limit.

        Args:
            image_path: Path to the image file

        Returns:
            Preprocessed image as bytes
        """
        try:
            img = Image.open(image_path)

            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Resize if too small (upscale only small images)
            width, height = img.size
            if width < 300 or height < 300:
                scale_factor = max(300 / height, 300 / width, 1.5)
                new_size = (int(width * scale_factor), int(height * scale_factor))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # Increase contrast and sharpness for better OCR
            img = ImageEnhance.Contrast(img).enhance(1.5)
            img = ImageEnhance.Sharpness(img).enhance(1.5)

            # Compress to stay within API size limit
            return self.compress_image_under_limit(img)

        except Exception as e:
            logger.error(f"Error in preprocessing: {str(e)}")
            # Fallback: read raw file; if it's oversized we'll catch it later
            with open(image_path, 'rb') as f:
                return f.read()

    def compress_raw_image(self, image_path: str) -> bytes:
        """
        Compress a raw image file (no enhancements) to fit the size limit.
        Used when preprocessing='none' but the file is still too large.

        Args:
            image_path: Path to the image file

        Returns:
            Compressed image bytes
        """
        try:
            file_size = os.path.getsize(image_path)
            if file_size <= MAX_FILE_SIZE_BYTES:
                # File is already small enough — read as-is
                with open(image_path, 'rb') as f:
                    return f.read()

            # File is too large — compress it
            logger.info(f"File {os.path.basename(image_path)} is {file_size / 1024:.1f} KB, compressing…")
            img = Image.open(image_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            return self.compress_image_under_limit(img)

        except Exception as e:
            logger.error(f"Error compressing raw image: {str(e)}")
            with open(image_path, 'rb') as f:
                return f.read()

    def extract_text_from_image(
        self,
        image_path: str,
        lang: str = 'eng',
        preprocessing: str = 'basic'
    ) -> Dict[str, any]:
        """
        Extract text from image using OCR.space API

        Args:
            image_path: Path to the image file
            lang: Language code (eng, spa, fra, deu, etc.)
            preprocessing: 'basic' or 'none'

        Returns:
            Dictionary with extracted text and confidence
        """
        temp_path = None
        try:
            # Prepare image bytes — always enforce the size limit
            if preprocessing == 'basic':
                image_bytes = self.preprocess_image_basic(image_path)
                filename = os.path.basename(image_path) + '.processed.jpg'
            else:
                image_bytes = self.compress_raw_image(image_path)
                filename = os.path.basename(image_path)

            # Write to a temp file so we can open it as a file object for requests
            temp_path = image_path + '.ocr_tmp.jpg'
            with open(temp_path, 'wb') as f:
                f.write(image_bytes)

            logger.debug(f"Sending {len(image_bytes) / 1024:.1f} KB to OCR.space")

            # Prepare API request
            with open(temp_path, 'rb') as f:
                payload = {
                    'apikey': self.api_key,
                    'language': lang,
                    'isOverlayRequired': False,
                    'detectOrientation': True,
                    'scale': True,
                    'OCREngine': 2  # Engine 2 is more accurate
                }

                files = {'file': (filename, f, 'image/jpeg')}

                # Make API request
                response = requests.post(
                    self.api_url,
                    files=files,
                    data=payload,
                    timeout=30
                )

            # Parse response
            result = response.json()

            if result.get('IsErroredOnProcessing'):
                error_msg = result.get('ErrorMessage', ['Unknown error'])[0]
                return {
                    'success': False,
                    'text': '',
                    'confidence': 0,
                    'error': f"OCR.space API error: {error_msg}"
                }

            # Extract text
            parsed_results = result.get('ParsedResults', [])
            if parsed_results:
                text = parsed_results[0].get('ParsedText', '')

                # OCR.space doesn't provide confidence, estimate based on text length
                confidence = 85.0 if len(text.strip()) > 10 else 70.0

                return {
                    'success': True,
                    'text': text.strip(),
                    'confidence': confidence,
                    'word_count': len(text.split()),
                    'error': None
                }
            else:
                return {
                    'success': False,
                    'text': '',
                    'confidence': 0,
                    'error': 'No text detected in image'
                }

        except Exception as e:
            logger.error(f"Error processing image {image_path}: {str(e)}")
            return {
                'success': False,
                'text': '',
                'confidence': 0,
                'error': str(e)
            }
        finally:
            # Always clean up temp file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    def extract_text_with_multiple_strategies(
        self,
        image_path: str,
        lang: str = 'eng'
    ) -> Dict[str, any]:
        """
        Try multiple OCR engines and preprocessing strategies

        Args:
            image_path: Path to the image file
            lang: Language code

        Returns:
            Best extraction result
        """
        strategies = [
            ('engine2_preprocessed', lambda: self.extract_text_from_image(image_path, lang, 'basic')),
            ('engine2_raw', lambda: self.extract_text_from_image(image_path, lang, 'none')),
        ]

        best_result = {'text': '', 'confidence': 0, 'strategy': 'none'}

        for strategy_name, strategy_func in strategies:
            try:
                result = strategy_func()

                # Score based on confidence and text length
                text_length = len(result.get('text', '').strip())
                confidence = result.get('confidence', 0)
                score = confidence * (1 + min(text_length / 100, 1.0))

                best_score = best_result.get('confidence', 0) * (
                    1 + min(len(best_result.get('text', '')) / 100, 1.0)
                )

                if result['success'] and score > best_score:
                    best_result = result
                    best_result['strategy'] = strategy_name

                # If we got excellent results, stop
                if result['success'] and confidence > 80 and text_length > 20:
                    logger.info(f"Good result with {strategy_name}, stopping")
                    break

            except Exception as e:
                logger.warning(f"Strategy {strategy_name} failed: {str(e)}")
                continue

        return best_result

    def extract_text_from_multiple_images(
        self,
        image_paths: List[str],
        separator: str = '\n\n',
        lang: str = 'eng',
        use_multiple_strategies: bool = True
    ) -> Dict[str, any]:
        """
        Extract text from multiple images in order

        Args:
            image_paths: List of image file paths
            separator: Text separator between images
            lang: Language code
            use_multiple_strategies: Try multiple strategies per image

        Returns:
            Dictionary with combined text and individual results
        """
        results = []
        combined_text_parts = []

        for idx, image_path in enumerate(image_paths):
            if use_multiple_strategies:
                result = self.extract_text_with_multiple_strategies(image_path, lang=lang)
            else:
                result = self.extract_text_from_image(image_path, lang=lang)

            result['order_index'] = idx
            result['image_path'] = image_path
            results.append(result)

            if result['success'] and result['text']:
                combined_text_parts.append(result['text'])

        combined_text = separator.join(combined_text_parts)

        return {
            'success': True,
            'combined_text': combined_text,
            'individual_results': results,
            'total_images': len(image_paths),
            'successful_extractions': sum(1 for r in results if r['success'])
        }

    def get_supported_languages(self) -> List[str]:
        """
        Get list of supported languages

        Returns:
            List of language codes
        """
        return [
            'ara', 'bul', 'chs', 'cht', 'hrv', 'cze', 'dan',
            'dut', 'eng', 'fin', 'fre', 'ger', 'gre', 'hun',
            'kor', 'ita', 'jpn', 'pol', 'por', 'rus', 'slv',
            'spa', 'swe', 'tur'
        ]

    def clean_text(self, text: str) -> str:
        """
        Clean extracted text

        Args:
            text: Raw extracted text

        Returns:
            Cleaned text
        """
        if not text:
            return ''

        # Remove extra whitespace
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]

        # Join with single newline
        cleaned_text = '\n'.join(lines)

        return cleaned_text