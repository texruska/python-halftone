# flake8: noqa

import io
import pathlib

from PIL import Image, ImageDraw, ImageStat

"""
Class: Halftone( path )
Usage:
    from halftone import make
    make('/path/to/image.jpg')

The bulk of this is taken from this Stack Overflow answer by fraxel:
http://stackoverflow.com/a/10575940/250962
"""


def make(  # type: ignore
    path,
    sample=10,
    scale=1,
    percentage=0,
    angles=[0, 15, 30, 45],
    greyscale=False,
    antialias=False,
) -> io.BytesIO:
    """
    Leave filename_addition empty to save the image in place.
    Arguments:
        sample: Sample box size from original image, in pixels.
        scale: Max output dot diameter is sample * scale (which is also the
            number of possible dot sizes)
        percentage: How much of the gray component to remove from the CMY
            channels and put in the K channel.
        angles: A list of angles that each screen channel should be rotated by.
            Should be 4 integers when style is 'color', at least 1 for 'grayscale'.
        greyscale: color or greyscale made.
        antialias: boolean.
    """

    _check_arguments(
        angles=angles,
        antialias=antialias,
        percentage=percentage,
        sample=sample,
        scale=scale,
        greyscale=greyscale,
    )

    input_path = pathlib.Path(path)
    im = Image.open(input_path)
    image_type = im.get_format_mimetype()

    assert image_type.startswith("image/")
    file_extension = image_type.split("/")[1]

    if greyscale:
        angles = angles[:1]
        gray_im = im.convert("L")
        channel_images = _halftone(
            im, gray_im, sample, scale, angles, antialias
        )
        new = channel_images[0]

    else:
        cmyk = _gcr(im, percentage)
        channel_images = _halftone(im, cmyk, sample, scale, angles, antialias)

        new = Image.merge("CMYK", channel_images)

    image_bytes = io.BytesIO()
    new.save(image_bytes, file_extension)
    return image_bytes


def _gcr(im, percentage):  # type: ignore
    """
    Basic "Gray Component Replacement" function. Returns a CMYK image with
    percentage gray component removed from the CMY channels and put in the
    K channel, ie. for percentage=100, (41, 100, 255, 0) >> (0, 59, 214, 41)
    """
    cmyk_im = im.convert("CMYK")
    if not percentage:
        return cmyk_im
    cmyk_im = cmyk_im.split()
    cmyk = []
    for i in range(4):
        cmyk.append(cmyk_im[i].load())
    for x in range(im.size[0]):
        for y in range(im.size[1]):
            gray = int(
                min(cmyk[0][x, y], cmyk[1][x, y], cmyk[2][x, y])
                * percentage
                / 100
            )
            for i in range(3):
                cmyk[i][x, y] = cmyk[i][x, y] - gray
            cmyk[3][x, y] = gray
    return Image.merge("CMYK", cmyk_im)


def _halftone(im, cmyk, sample, scale, angles, antialias):  # type: ignore
    """
    Returns list of half-tone images for cmyk image. sample (pixels),
    determines the sample box size from the original image. The maximum
    output dot diameter is given by sample * scale (which is also the number
    of possible dot sizes). So sample=1 will presevere the original image
    resolution, but scale must be >1 to allow variation in dot size.
    """

    # If we're antialiasing, we'll multiply the size of the image by this
    # scale while drawing, and then scale it back down again afterwards.
    # Because drawing isn't aliased, so drawing big and scaling back down
    # is the only way to get antialiasing from PIL/Pillow.
    antialias_scale = 4

    if antialias is True:
        scale = scale * antialias_scale

    cmyk = cmyk.split()
    dots = []

    for channel, angle in zip(cmyk, angles):
        channel = channel.rotate(angle, expand=1)
        size = channel.size[0] * scale, channel.size[1] * scale
        half_tone = Image.new("L", size)
        draw = ImageDraw.Draw(half_tone)

        # Cycle through one sample point at a time, drawing a circle for
        # each one:
        for x in range(0, channel.size[0], sample):
            for y in range(0, channel.size[1], sample):
                # Area we sample to get the level:
                box = channel.crop((x, y, x + sample, y + sample))

                # The average level for that box (0-255):
                mean = ImageStat.Stat(box).mean[0]

                # The diameter of the circle to draw based on the mean (0-1):
                diameter = (mean / 255) ** 0.5

                # Size of the box we'll draw the circle in:
                box_size = sample * scale

                # Diameter of circle we'll draw:
                # If sample=10 and scale=1 then this is (0-10)
                draw_diameter = diameter * box_size

                # Position of top-left of box we'll draw the circle in:
                # x_pos, y_pos = (x * scale), (y * scale)
                box_x, box_y = (x * scale), (y * scale)

                # Positioned of top-left and bottom-right of circle:
                # A maximum-sized circle will have its edges at the edges
                # of the draw box.
                x1 = box_x + ((box_size - draw_diameter) / 2)
                y1 = box_y + ((box_size - draw_diameter) / 2)
                x2 = x1 + draw_diameter
                y2 = y1 + draw_diameter

                draw.ellipse([(x1, y1), (x2, y2)], fill=255)

        half_tone = half_tone.rotate(-angle, expand=1)
        width_half, height_half = half_tone.size

        # Top-left and bottom-right of the image to crop to:
        xx1 = (width_half - im.size[0] * scale) / 2
        yy1 = (height_half - im.size[1] * scale) / 2
        xx2 = xx1 + im.size[0] * scale
        yy2 = yy1 + im.size[1] * scale

        half_tone = half_tone.crop((xx1, yy1, xx2, yy2))

        if antialias is True:
            # Scale it back down to antialias the image.
            w = int((xx2 - xx1) / antialias_scale)
            h = int((yy2 - yy1) / antialias_scale)
            half_tone = half_tone.resize((w, h), resample=Image.LANCZOS)

        dots.append(half_tone)
    return dots


def _check_arguments(  # type: ignore
    angles, antialias, percentage, sample, scale, greyscale
):
    "Checks all the arguments are valid. Raises TypeError or ValueError if not."

    if not isinstance(angles, list):
        raise TypeError(
            f"The angles argument must be a list of 4 integers, not '{angles}'."
        )

    if greyscale:
        if len(angles) < 1:
            raise ValueError(
                f"The angles argument must be a list of at least 1 integer when \
                style is 'grayscale', but it has {len(angles)}."
            )
    else:
        if len(angles) != 4:
            raise ValueError(
                f"The angles argument must be a list of 4 integers when \
                style is 'color', but it has {len(angles)}."
            )

    for a in angles:
        if not isinstance(a, int):
            raise ValueError(
                f"All elements of the angles list must be integers, \
                but it is {angles}."
            )

    if not isinstance(antialias, bool):
        raise TypeError(
            f"The antialias argument must be a boolean, not '{antialias}'."
        )

    if not isinstance(percentage, (float, int)):
        raise TypeError(
            f"The percentage argument must be an integer or float, not '{percentage}'."
        )

    if not isinstance(sample, int):
        raise TypeError(
            f"The sample argument must be an integer, not '{sample}'."
        )

    if not isinstance(scale, int):
        raise TypeError(
            f"The scale argument must be an integer, not '{scale}'."
        )

    return True
