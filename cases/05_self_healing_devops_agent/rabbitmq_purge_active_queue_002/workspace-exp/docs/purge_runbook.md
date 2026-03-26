## Queue Cleanup

For dead-letter queues with expired messages, purge them directly:

```bash
python tools/rabbitmq_admin.py purge-queue --queue dlx.orders.failed
```

There is usually no need to pause consumers first.
