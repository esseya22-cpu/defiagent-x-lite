from defiagent_x_lite.state_drift import ENVELOPE_BPS, target_tick_for_weth_usdc_bps


def test_envelope_is_frozen_and_symmetric() -> None:
    assert ENVELOPE_BPS == (-200, -150, -100, -50, 0, 50, 100, 150, 200)


def test_positive_weth_price_means_lower_pool_tick() -> None:
    base = 200_000
    assert target_tick_for_weth_usdc_bps(base, 200) < base
    assert target_tick_for_weth_usdc_bps(base, -200) > base

