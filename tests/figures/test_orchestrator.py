from scripts import plot_subq1_results as P


def test_manifest_lists_all_twelve_figures():
    assert len(P.FIGURES) == 12
    names = {f["name"] for f in P.FIGURES}
    assert names == {"F1", "F2", "F3", "F4", "F4b", "F5", "F6",
                     "F7", "F8", "F9", "F10", "F11"}


def test_every_figure_declares_its_output_filename():
    for f in P.FIGURES:
        assert f["out"].endswith(".png")
        assert f["resolution"] in ("hourly", "5-min")


def test_no_two_figures_write_the_same_file():
    # A duplicated filename silently drops a figure from the set, and the
    # count test above would still pass.
    outs = [f["out"] for f in P.FIGURES]
    assert len(set(outs)) == len(outs), outs


def test_every_manifest_name_is_actually_dispatched():
    # The manifest and the if-ladder in main() are two lists that must not
    # drift apart; a name present in one and absent from the other means a
    # figure that never regenerates.
    import inspect
    src = inspect.getsource(P.main)
    for f in P.FIGURES:
        assert f'"{f["name"]}" in want' in src, f'{f["name"]} never dispatched'
