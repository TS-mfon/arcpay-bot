"""Receipt image generator using Pillow."""

import io
from datetime import datetime, timezone
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from bot.utils.formatting import format_usdc, format_address, format_tx_hash


class ReceiptGenerator:
    """Generates receipt images for transactions."""

    WIDTH = 600
    PADDING = 40
    BG_COLOR = (255, 255, 255)
    TEXT_COLOR = (33, 33, 33)
    ACCENT_COLOR = (46, 125, 50)  # Green
    LIGHT_GRAY = (200, 200, 200)
    HEADER_BG = (46, 125, 50)
    HEADER_TEXT = (255, 255, 255)

    def generate_receipt(
        self,
        from_name: str,
        to_name: str,
        amount: float,
        memo: Optional[str],
        tx_hash: Optional[str],
        timestamp: Optional[str] = None,
    ) -> io.BytesIO:
        """Generate a receipt image and return as a BytesIO buffer.

        Returns:
            BytesIO buffer containing the PNG image.
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        # Calculate image height
        height = 480
        if memo:
            height += 40

        img = Image.new("RGB", (self.WIDTH, height), self.BG_COLOR)
        draw = ImageDraw.Draw(img)

        # Use default font (Pillow built-in)
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except (OSError, IOError):
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()

        y = 0

        # Header
        draw.rectangle([(0, 0), (self.WIDTH, 80)], fill=self.HEADER_BG)
        draw.text(
            (self.PADDING, 25),
            "ArcPay Receipt",
            fill=self.HEADER_TEXT,
            font=font_large,
        )

        y = 100

        # Separator
        draw.line(
            [(self.PADDING, y), (self.WIDTH - self.PADDING, y)],
            fill=self.LIGHT_GRAY,
            width=1,
        )
        y += 20

        # Amount (centered, large)
        amount_text = format_usdc(amount)
        bbox = draw.textbbox((0, 0), amount_text, font=font_large)
        text_width = bbox[2] - bbox[0]
        draw.text(
            ((self.WIDTH - text_width) / 2, y),
            amount_text,
            fill=self.ACCENT_COLOR,
            font=font_large,
        )
        y += 50

        # From
        draw.text(
            (self.PADDING, y), "From:", fill=self.LIGHT_GRAY, font=font_small
        )
        y += 20
        draw.text(
            (self.PADDING, y), from_name, fill=self.TEXT_COLOR, font=font_medium
        )
        y += 35

        # To
        draw.text(
            (self.PADDING, y), "To:", fill=self.LIGHT_GRAY, font=font_small
        )
        y += 20
        draw.text(
            (self.PADDING, y), to_name, fill=self.TEXT_COLOR, font=font_medium
        )
        y += 35

        # Memo
        if memo:
            draw.text(
                (self.PADDING, y), "Memo:", fill=self.LIGHT_GRAY, font=font_small
            )
            y += 20
            draw.text(
                (self.PADDING, y), memo, fill=self.TEXT_COLOR, font=font_medium
            )
            y += 35

        # Separator
        draw.line(
            [(self.PADDING, y), (self.WIDTH - self.PADDING, y)],
            fill=self.LIGHT_GRAY,
            width=1,
        )
        y += 20

        # Transaction hash
        if tx_hash:
            draw.text(
                (self.PADDING, y),
                "Transaction:",
                fill=self.LIGHT_GRAY,
                font=font_small,
            )
            y += 20
            draw.text(
                (self.PADDING, y),
                format_tx_hash(tx_hash),
                fill=self.TEXT_COLOR,
                font=font_small,
            )
            y += 30

        # Timestamp
        draw.text(
            (self.PADDING, y), "Date:", fill=self.LIGHT_GRAY, font=font_small
        )
        y += 20
        draw.text(
            (self.PADDING, y), timestamp, fill=self.TEXT_COLOR, font=font_small
        )
        y += 35

        # Footer
        draw.text(
            (self.PADDING, y),
            "Powered by Arc Network",
            fill=self.LIGHT_GRAY,
            font=font_small,
        )

        # Save to buffer
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer
