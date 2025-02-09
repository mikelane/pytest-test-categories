from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest


class DescribeReportOutput:
    def it_displays_test_size_summary(self, pytester: pytest.Pytester) -> None:
        """Verify that a summary of test sizes is displayed after the test run."""
        pytester.makepyfile(
            test_example="""
            import pytest

            @pytest.mark.small
            def test_small_1():
                assert True

            @pytest.mark.small
            def test_small_2():
                assert True

            @pytest.mark.small
            def test_small_3():
                assert True

            @pytest.mark.small
            def test_small_4():
                assert True

            @pytest.mark.small
            def test_small_5():
                assert True

            @pytest.mark.small
            def test_small_6():
                assert True

            @pytest.mark.small
            def test_small_7():
                assert True

            @pytest.mark.small
            def test_small_8():
                assert True

            @pytest.mark.small
            def test_small_9():
                assert True

            @pytest.mark.small
            def test_small_10():
                assert True

            @pytest.mark.small
            def test_small_11():
                assert True

            @pytest.mark.medium
            def test_medium_1():
                assert True

            @pytest.mark.medium
            def test_medium_2():
                assert True

            @pytest.mark.xlarge
            def test_xlarge_1():
                assert True
            """
        )

        result = pytester.runpytest('-vv')

        # Then the output should include a summary of test sizes
        result.stdout.fnmatch_lines(
            [
                '*Test Suite Distribution Summary*',
                '*Test Size Distribution:*',
                '*Small*11*test*(78.57%)*',
                '*Medium*2*test*(14.29%)*',
                '*Large*0*test*(0.00%)*',
                '*XLarge*1*test*(7.14%)*',
                '*Status: Great job! Your test distribution is on track.*',
            ]
        )

    def it_warns_when_too_many_large_tests(self, pytester: pytest.Pytester) -> None:
        """Verify that appropriate warning is shown when there are too many large/xlarge tests."""
        pytester.makepyfile(
            test_example="""
                import pytest

                @pytest.mark.small
                def test_small_1():
                    assert True

                @pytest.mark.small
                def test_small_2():
                    assert True

                @pytest.mark.medium
                def test_medium_1():
                    assert True

                @pytest.mark.large
                def test_large_1():
                    assert True

                @pytest.mark.xlarge
                def test_xlarge_1():
                    assert True
                """
        )

        result = pytester.runpytest('-vv')

        # Then the output should include appropriate distribution warning
        result.stdout.fnmatch_lines(
            [
                '*Test Suite Distribution Summary*',
                '*Test Size Distribution:*',
                '*Small*2*tests*(40.00%)*',  # Below target of 75-85%
                '*Medium*1*test*(20.00%)*',  # At upper target of 10-20%
                '*Large*1*test*(20.00%)*',  # Combined Large/XLarge at 40%
                '*XLarge*1*test*(20.00%)*',  # Way above target of 2-8%
                '*Status: Warning! Distribution needs improvement:*',
                '*Large/XLarge tests are 40% of the suite (target: 2-8%)*',
                '*This indicates too many complex tests. Consider:*',
                '*Breaking large tests into smaller focused tests*',
                '*Moving test setup into fixtures*',
                '*Using test parameterization for repeated scenarios*',
            ]
        )

    def it_warns_when_too_few_small_tests(self, pytester: pytest.Pytester) -> None:
        """Verify that appropriate warning is shown when there are too few small tests."""
        pytester.makepyfile(
            test_example="""
                import pytest

                @pytest.mark.small
                def test_small_1():
                    assert True

                @pytest.mark.small
                def test_small_2():
                    assert True

                @pytest.mark.medium
                def test_medium_1():
                    assert True

                @pytest.mark.medium
                def test_medium_2():
                    assert True

                @pytest.mark.medium
                def test_medium_3():
                    assert True

                @pytest.mark.medium
                def test_medium_4():
                    assert True
                """
        )

        result = pytester.runpytest('-vv')

        # Then the output should include appropriate distribution warning
        result.stdout.fnmatch_lines(
            [
                '*Test Suite Distribution Summary*',
                '*Test Size Distribution:*',
                '*Small*2*tests*(33.33%)*',  # Well below target of 75-85%
                '*Medium*4*tests*(66.67%)*',  # Well above target of 10-20%
                '*Large*0*tests*(0.00%)*',
                '*XLarge*0*tests*(0.00%)*',
                '*Status: Warning! Distribution needs improvement:*',
                '*Small tests are only 33.33% of the suite (target: 75-85%)*',
                '*This indicates tests may be too complex. Consider:*',
                '*Breaking down medium tests into smaller units*',
                '*Testing more specific behaviors individually*',
                '*Moving complex setup into fixtures or helpers*',
            ]
        )

    def it_warns_when_too_many_medium_tests(self, pytester: pytest.Pytester) -> None:
        """Verify that appropriate warning is shown when there are too many medium tests."""
        pytester.makepyfile(
            test_example="""
                import pytest

                @pytest.mark.small
                def test_small_1():
                    assert True

                @pytest.mark.small
                def test_small_2():
                    assert True

                @pytest.mark.small
                def test_small_3():
                    assert True

                @pytest.mark.small
                def test_small_4():
                    assert True

                @pytest.mark.medium
                def test_medium_1():
                    assert True

                @pytest.mark.medium
                def test_medium_2():
                    assert True
                """
        )

        result = pytester.runpytest('-vv')

        # Then the output should include appropriate distribution warning
        result.stdout.fnmatch_lines(
            [
                '*Test Suite Distribution Summary*',
                '*Test Size Distribution:*',
                '*Small*4*tests*(66.67%)*',  # Below target of 75-85%, but that's not our focus
                '*Medium*2*tests*(33.33%)*',  # Above target of 10-20%
                '*Large*0*tests*(0.00%)*',
                '*XLarge*0*tests*(0.00%)*',
                '*Status: Warning! Distribution needs improvement:*',
                '*Medium tests are 33.33% of the suite (target: 10-20%)*',
                '*This suggests test complexity is creeping up. Consider:*',
                '*Identifying shared setup that could be simplified*',
                '*Looking for tests that could be split into smaller units*',
                '*Reviewing test dependencies and fixture usage*',
            ]
        )

    def it_warns_when_moderately_too_few_small_tests(self, pytester: pytest.Pytester) -> None:
        """Verify warning is shown when small tests are moderately below target."""
        pytester.makepyfile(
            test_example="""
                import pytest

                @pytest.mark.small
                def test_small_1():
                    assert True

                @pytest.mark.small
                def test_small_2():
                    assert True

                @pytest.mark.small
                def test_small_3():
                    assert True

                @pytest.mark.small
                def test_small_4():
                    assert True

                @pytest.mark.small
                def test_small_5():
                    assert True

                @pytest.mark.small
                def test_small_6():
                    assert True

                @pytest.mark.small
                def test_small_7():
                    assert True

                @pytest.mark.small
                def test_small_8():
                    assert True

                @pytest.mark.medium
                def test_medium_1():
                    assert True

                @pytest.mark.medium
                def test_medium_2():
                    assert True

                @pytest.mark.medium
                def test_medium_3():
                    assert True

                @pytest.mark.medium
                def test_medium_4():
                    assert True

                @pytest.mark.large
                def test_large_1():
                    assert True
            """
        )

        result = pytester.runpytest('-vv')

        # Then the output should include appropriate distribution warning
        result.stdout.fnmatch_lines(
            [
                '*Test Suite Distribution Summary*',
                '*Test Size Distribution:*',
                '*Small*8*tests*(61.54%)*',  # Below target of 75-85%, but above critical 50%
                '*Medium*4*tests*(30.77%)*',  # Higher than ideal but not the primary issue
                '*Large*1*test*(7.69%)*',  # Combined Large/XLarge just over 7%
                '*XLarge*0*tests*(0.00%)*',
                '*Status: Warning! Distribution needs improvement:*',
                '*Small tests are only 61.54% of the suite (target: 75-85%)*',
                '*This indicates tests may be too complex. Consider:*',
                '*Breaking down medium tests into smaller units*',
                '*Testing more specific behaviors individually*',
                '*Moving complex setup into fixtures or helpers*',
            ]
        )
