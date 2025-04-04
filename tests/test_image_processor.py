import pytest
from pathlib import Path
import requests
from unittest.mock import Mock, patch, mock_open

from imas_standard_names.image_processor import ImageProcessor


@pytest.fixture
def mock_urls():
    """Return list of mock urls."""
    return [
        "https://github.com/user-attachments/assets/12345/image1.jpg",
        "https://github.com/user-attachments/assets/67890/image2.png",
        "https://github.com/user-attachments/assets/11223/image3.gif",
        "https://github.com/user-attachments/assets/44556/image4.svg",
        "https://github.com/user-attachments/assets/77889/image5.webp",
    ]


@pytest.fixture
def mock_response():
    """Create a mock HTTP response with image content based on image type."""

    def _mock_response(content_type):
        mock = Mock(spec=requests.Response)
        mock.headers = {"content-type": content_type}
        mock.iter_content.return_value = [b"test image data"]
        return mock

    return _mock_response


@pytest.fixture
def sample_documentation(mock_urls):
    """Create sample documentation with GitHub user-attachment URLs for all image types."""
    return """
    # Sample Documentation
    
    This is a test documentation with images.

    """ + "\n".join(
        f"![{url.split('.')[-1].upper()} Image]({url})" for url in mock_urls
    )


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for test images."""
    img_dir = tmp_path / "docs" / "img"
    img_dir.mkdir(parents=True)
    return img_dir


def test_url_extraction(sample_documentation, mock_urls):
    """Test that GitHub user-attachment URLs are correctly extracted."""
    urls = ImageProcessor("test_name", sample_documentation).urls

    # Check that the URLs are correctly extracted
    assert len(urls) == len(mock_urls)
    for url in mock_urls:
        assert url in urls


def test_path_extraction(sample_documentation, mock_urls):
    """Test that paths are correctly generated from URLs."""
    files = ImageProcessor("test_name", sample_documentation, "images").files

    # Check that the paths are correctly generated
    assert len(files) == len(mock_urls)
    for index, url in enumerate(mock_urls, 1):
        expected_extension = url.split(".")[-1]
        expected_path = (Path("images") / f"test_name-{index}").with_suffix(
            f".{expected_extension}"
        )
        assert expected_path in files


def test_documentation_with_relative_paths(sample_documentation, mock_urls):
    """Test that documentation is correctly modified with relative paths."""
    processor = ImageProcessor("test_name", sample_documentation, "images")
    modified_docs = processor.documentation_with_relative_paths()

    # Check that the URLs are replaced with relative paths
    for index, url in enumerate(mock_urls, 1):
        expected_path = (Path("images") / f"test_name-{index}").with_suffix(
            f".{url.split('.')[-1]}"
        )
        assert str(expected_path) in modified_docs


def test_no_images_in_documentation():
    """Test processing documentation with no images."""
    docs = "This is a test documentation with no images."
    processor = ImageProcessor("test_name", docs)

    # Assert that the documentation is unchanged
    assert docs == processor.documentation_with_relative_paths()


@patch("builtins.open", new_callable=mock_open)
@patch("requests.get")
def test_image_content_writing(mock_get, mock_file, mock_response, temp_dir):
    """Test that image content is correctly written to file."""
    # Set up the mock response
    mock_get.return_value = mock_response("image/png")

    # Create an image processor
    processor = ImageProcessor(
        "test_name",
        "![test](https://github.com/user-attachments/assets/12345/test.png)",
        str(temp_dir.parent),
    )

    # Call the download method
    processor.download_images()

    # Check that the file was opened for writing
    assert mock_file.call_count >= 1

    # Check that the image content was written to the file
    handle = mock_file()
    handle.write.assert_called_with(b"test image data")


@pytest.mark.parametrize(
    "content_type, extension",
    [
        ("image/jpeg", "jpg"),
        ("image/png", "png"),
        ("image/gif", "gif"),
        ("image/svg+xml", "svg"),
        ("image/webp", "webp"),
    ],
)
def test_extension_mapping(content_type, extension, mock_response):
    """Test that the correct file extension is determined for each content type."""
    mock_response = mock_response(content_type)
    with patch("requests.get", return_value=mock_response):
        processor = ImageProcessor("test_name", "")
        result = processor._extension(
            "https://github.com/user-attachments/assets/12345/test"
        )
        assert result == extension


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__])
