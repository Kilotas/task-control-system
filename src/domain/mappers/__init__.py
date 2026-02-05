from __future__ import annotations


def __getattr__(name: str):
    if name == "to_created_out":
        from .batch_mapper import to_created_out
        return to_created_out
    elif name == "to_subscription_out":
        from .webhook_mapper import to_subscription_out
        return to_subscription_out
    elif name == "to_subscription_list_out":
        from .webhook_mapper import to_subscription_list_out
        return to_subscription_list_out
    elif name == "to_delivery_out":
        from .webhook_mapper import to_delivery_out
        return to_delivery_out
    elif name == "to_delivery_list_out":
        from .webhook_mapper import to_delivery_list_out
        return to_delivery_list_out
    elif name == "to_dashboard_out":
        from .analytics_mapper import to_dashboard_out
        return to_dashboard_out
    elif name == "to_batch_statistics_out":
        from .analytics_mapper import to_batch_statistics_out
        return to_batch_statistics_out
    elif name == "to_compare_batches_out":
        from .analytics_mapper import to_compare_batches_out
        return to_compare_batches_out
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "to_created_out",
    "to_subscription_out",
    "to_subscription_list_out",
    "to_delivery_out",
    "to_delivery_list_out",
    "to_dashboard_out",
    "to_batch_statistics_out",
    "to_compare_batches_out",
]
