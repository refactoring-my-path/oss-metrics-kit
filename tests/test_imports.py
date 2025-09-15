def test_import_package():
    import importlib

    assert importlib.import_module("ossmk")
    assert importlib.import_module("ossmk.cli")

