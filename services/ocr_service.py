import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np
import os
from typing import List, Dict, Optional
import logging
import re

logger = logging.getLogger(__name__)


class OCRService:
    """
    Enhanced service for extracting text from images using Tesseract OCR
    with advanced preprocessing for better accuracy
    """

    def __init__(self):
        # Configure Tesseract path for Windows
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

        # For Linux/Mac, use:
        # pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'

    def detect_and_correct_orientation(self, image):
        """
        Detect text orientation and rotate image if needed

        Args:
            image: OpenCV image (numpy array)

        Returns:
            Corrected image
        """
        try:
            # Try to detect orientation using OSD (Orientation and Script Detection)
            osd = pytesseract.image_to_osd(image)
            rotation = int(re.search(r'(?<=Rotate: )\d+', osd).group(0))

            if rotation != 0:
                # Rotate image
                if rotation == 90:
                    image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
                elif rotation == 180:
                    image = cv2.rotate(image, cv2.ROTATE_180)
                elif rotation == 270:
                    image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)

                logger.info(f"Corrected rotation by {rotation} degrees")
        except Exception as e:
            logger.warning(f"Could not detect orientation: {str(e)}")

        return image

    def preprocess_image_advanced(self, image_path: str, detect_orientation: bool = True) -> np.ndarray:
        """
        Advanced image preprocessing for better OCR accuracy

        Args:
            image_path: Path to the image file
            detect_orientation: Whether to detect and correct orientation

        Returns:
            Preprocessed image as numpy array
        """
        try:
            # Read image with OpenCV
            img = cv2.imread(image_path)

            if img is None:
                raise ValueError(f"Could not read image: {image_path}")

            # Detect and correct orientation if needed
            if detect_orientation:
                img = self.detect_and_correct_orientation(img)

            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Resize if image is too small (helps with OCR accuracy)
            height, width = gray.shape
            if height < 300 or width < 300:
                scale_factor = max(300 / height, 300 / width, 2.0)
                gray = cv2.resize(gray, None, fx=scale_factor, fy=scale_factor,
                                  interpolation=cv2.INTER_CUBIC)

            # Apply denoising
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

            # Increase contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            contrast = clahe.apply(denoised)

            # Apply adaptive thresholding for better text extraction
            thresh = cv2.adaptiveThreshold(
                contrast, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11, 2
            )

            # Morphological operations to clean up
            kernel = np.ones((1, 1), np.uint8)

            # Remove noise
            opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)

            # Close gaps in text
            closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel, iterations=1)

            return closing

        except Exception as e:
            logger.error(f"Error in advanced preprocessing: {str(e)}")
            # Fallback to basic preprocessing
            return self.preprocess_image_basic(image_path)

    def preprocess_image_basic(self, image_path: str) -> Image.Image:
        """
        Basic image preprocessing using PIL

        Args:
            image_path: Path to the image file

        Returns:
            Preprocessed PIL Image
        """
        try:
            img = Image.open(image_path)

            # Convert to grayscale
            img = img.convert('L')

            # Resize if too small
            width, height = img.size
            if width < 300 or height < 300:
                scale_factor = max(300 / height, 300 / width, 2.0)
                new_size = (int(width * scale_factor), int(height * scale_factor))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # Increase contrast
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)

            # Increase sharpness
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(2.0)

            # Apply threshold
            img = img.point(lambda x: 0 if x < 140 else 255, '1')

            return img

        except Exception as e:
            logger.error(f"Error in basic preprocessing: {str(e)}")
            return Image.open(image_path)

    def extract_text_from_image(self, image_path: str, lang: str = 'eng',
                                preprocessing: str = 'advanced') -> Dict[str, any]:
        """
        Extract text from a single image with multiple OCR strategies

        Args:
            image_path: Path to the image file
            lang: Language for OCR (default: 'eng')
            preprocessing: 'advanced', 'basic', or 'none'

        Returns:
            Dictionary with extracted text and confidence
        """
        try:
            # Try multiple PSM (Page Segmentation Mode) configurations
            # Reordered to prioritize modes better for general text
            psm_modes = [
                3,  # Fully automatic page segmentation (default)
                6,  # Assume a single uniform block of text
                4,  # Assume a single column of text of variable sizes
                1,  # Automatic page segmentation with OSD
                11,  # Sparse text. Find as much text as possible
                12,  # Sparse text with OSD
            ]

            best_result = {'text': '', 'confidence': 0}

            for psm in psm_modes:
                try:
                    if preprocessing == 'advanced':
                        # Use OpenCV preprocessing
                        img_array = self.preprocess_image_advanced(image_path)
                        # Convert numpy array to PIL Image for pytesseract
                        img = Image.fromarray(img_array)
                    elif preprocessing == 'basic':
                        img = self.preprocess_image_basic(image_path)
                    else:
                        img = Image.open(image_path)

                    # Configure OCR with better settings
                    # OEM 3 = Default, based on what is available (LSTM + Legacy)
                    custom_config = f'--oem 3 --psm {psm} -c preserve_interword_spaces=1'

                    # Extract text
                    text = pytesseract.image_to_string(img, lang=lang, config=custom_config)

                    # Get confidence
                    try:
                        data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
                        confidences = [int(conf) for conf in data['conf'] if conf != '-1']
                        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                    except:
                        avg_confidence = 0

                    # Keep the result with highest confidence and meaningful text
                    if avg_confidence > best_result['confidence'] and len(text.strip()) > 0:
                        best_result = {
                            'text': text.strip(),
                            'confidence': avg_confidence,
                            'psm': psm
                        }

                    # If we got good confidence and meaningful text, stop trying
                    if avg_confidence > 75 and len(text.strip()) > 10:
                        break

                except Exception as e:
                    logger.warning(f"PSM {psm} failed: {str(e)}")
                    continue

            if best_result['text']:
                return {
                    'success': True,
                    'text': best_result['text'],
                    'confidence': best_result['confidence'],
                    'psm_used': best_result.get('psm', 3),
                    'error': None
                }
            else:
                return {
                    'success': False,
                    'text': '',
                    'confidence': 0,
                    'error': 'No text extracted from any PSM mode'
                }

        except Exception as e:
            logger.error(f"Error processing image {image_path}: {str(e)}")
            return {
                'success': False,
                'text': '',
                'confidence': 0,
                'error': str(e)
            }

    def extract_text_with_multiple_strategies(self, image_path: str, lang: str = 'eng') -> Dict[str, any]:
        """
        Try multiple preprocessing strategies and return the best result

        Args:
            image_path: Path to the image file
            lang: Language for OCR

        Returns:
            Best extraction result
        """
        strategies = ['advanced', 'basic', 'none']
        best_result = {'text': '', 'confidence': 0}

        for strategy in strategies:
            result = self.extract_text_from_image(image_path, lang, preprocessing=strategy)

            # Prioritize results with both good confidence AND meaningful length
            text_length = len(result.get('text', '').strip())
            confidence = result.get('confidence', 0)

            # Score combining confidence and text length
            score = confidence * (1 + min(text_length / 100, 1.0))
            best_score = best_result.get('confidence', 0) * (1 + min(len(best_result.get('text', '')) / 100, 1.0))

            if result['success'] and score > best_score:
                best_result = result
                best_result['strategy'] = strategy

            # If we got excellent results, stop
            if result['success'] and confidence > 80 and text_length > 20:
                break

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
            image_paths: List of image file paths in desired order
            separator: Text to use between images (default: double newline)
            lang: Language for OCR
            use_multiple_strategies: Try multiple preprocessing strategies

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
        """Get list of installed Tesseract languages"""
        try:
            langs = pytesseract.get_languages()
            return langs
        except Exception as e:
            logger.error(f"Error getting languages: {str(e)}")
            return ['eng']  # Default to English

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
        lines = [line for line in lines if line]  # Remove empty lines

        # Join with single newline
        cleaned_text = '\n'.join(lines)

        return cleaned_text

    def enhance_image_for_display(self, image_path: str, output_path: str) -> bool:
        """
        Save a preprocessed version of the image for user to see

        Args:
            image_path: Input image path
            output_path: Where to save enhanced image

        Returns:
            Success boolean
        """
        try:
            img_array = self.preprocess_image_advanced(image_path)
            cv2.imwrite(output_path, img_array)
            return True
        except Exception as e:
            logger.error(f"Error saving enhanced image: {str(e)}")
            return False