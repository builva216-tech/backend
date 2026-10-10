def post_worker_init(worker):
    from apps.core.bug_mail import start_report_worker
    worker.report_mail_stop = start_report_worker()


def worker_exit(server, worker):
    stop = getattr(worker, 'report_mail_stop', None)
    if stop is not None:
        stop.set()
