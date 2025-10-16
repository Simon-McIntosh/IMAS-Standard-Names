"""Test catalog state management fixes for create/write failures."""


def test_create_detects_duplicate_in_pending_changes(
    temp_catalog, temp_edit_catalog, invoke_async
):
    """Test that create tool detects duplicates in pending changes, not just base catalog."""
    from imas_standard_names.tools.create import CreateTool

    create_tool = CreateTool(temp_catalog, temp_edit_catalog)

    # Create first entry with valid data
    entry1 = {
        "name": "plasma_current",
        "kind": "scalar",
        "description": "Total toroidal plasma current.",
        "unit": "A",
    }
    result1 = invoke_async(create_tool, "create_standard_names", entries=[entry1])
    assert result1["summary"]["successful"] == 1

    # Try to create duplicate - should fail
    entry2 = {
        "name": "plasma_current",
        "kind": "scalar",
        "description": "Duplicate entry.",
        "unit": "A",
    }
    result2 = invoke_async(create_tool, "create_standard_names", entries=[entry2])
    assert result2["summary"]["failed"] == 1
    assert "exists" in result2["results"][0]["error"]["message"].lower()


def test_write_persistence(temp_catalog, temp_edit_catalog, invoke_async):
    """Test that successful write persists entries correctly."""
    from imas_standard_names.tools.create import CreateTool
    from imas_standard_names.tools.write import WriteTool

    create_tool = CreateTool(temp_catalog, temp_edit_catalog)
    write_tool = WriteTool(temp_catalog, temp_edit_catalog)

    # Create entry
    entry = {
        "name": "test_quantity",
        "kind": "scalar",
        "description": "Test quantity for write test.",
        "unit": "m",
    }
    result = invoke_async(create_tool, "create_standard_names", entries=[entry])
    assert result["summary"]["successful"] == 1

    # Entry should exist in memory
    assert temp_catalog.get("test_quantity") is not None

    # Write to disk
    write_result = invoke_async(write_tool, "write_standard_names")
    assert write_result["success"] is True
    assert write_result["written"] is True

    # Entry should still exist after successful write
    assert temp_catalog.get("test_quantity") is not None


def test_tag_validation_during_creation(temp_catalog, temp_edit_catalog, invoke_async):
    """Test that invalid tags are rejected during entry creation."""
    from imas_standard_names.tools.create import CreateTool

    create_tool = CreateTool(temp_catalog, temp_edit_catalog)

    # Create entry with invalid tag (not in vocabulary)
    entry = {
        "name": "test_bad_tags",
        "kind": "scalar",
        "description": "Test entry with invalid tags.",
        "unit": "m",
        "tags": ["nonexistent-tag-that-should-fail"],
    }
    result = invoke_async(create_tool, "create_standard_names", entries=[entry])
    # Should fail validation
    assert result["summary"]["failed"] == 1
