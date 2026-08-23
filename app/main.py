from fastapi import FastAPI, Depends , Query , HTTPException
from sqlalchemy.orm import Session

from .database import engine, SessionLocal
from .models import Base, Log
from .schemas import LogCreate, LogCreateResponse, LogResponse , LogBatchCreate
from sqlalchemy import func
from datetime import datetime, timedelta


app = FastAPI()


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@app.get("/")
def root():
    return {"message": "Log Ingestion Service is running"}


@app.post("/logs", response_model=LogCreateResponse)
def create_log(log: LogCreate, db: Session = Depends(get_db)):
    new_log = Log(
        timestamp=log.timestamp,
        level=log.level,
        service=log.service,
        message=log.message,
        attributes=log.attributes,
    )

    db.add(new_log)
    db.commit()
    db.refresh(new_log)

    return {
        "id": new_log.id,
        "message": "Log stored successfully",
    }

@app.post("/logs/batch")
def create_logs_batch(
    batch: LogBatchCreate,
    db: Session = Depends(get_db),
):
    new_logs = [
        Log(
            timestamp=log.timestamp,
            level=log.level,
            service=log.service,
            message=log.message,
            attributes=log.attributes,
        )
        for log in batch.logs
    ]

    db.add_all(new_logs)
    db.commit()

    return {
        "count": len(new_logs),
        "message": "Logs stored successfully",
    }

@app.get("/logs", response_model=list[LogResponse])
def get_logs(
    service: str | None = None,
    level: str | None = None,
    message: str | None = None,
    user_id: int | None = None,
    attribute: list[str] | None = Query(default=None),
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    if start_time is not None and end_time is not None:
        if start_time > end_time:
            raise HTTPException(
                status_code=400,
                detail="start_time must be earlier than or equal to end_time",
            )
    query = db.query(Log)

    if service is not None:
        query = query.filter(Log.service == service)

    if level is not None:
        query = query.filter(Log.level == level)

    if message is not None:
        query = query.filter(Log.message.ilike(f"%{message}%"))

    if user_id is not None:
        query = query.filter(Log.attributes["user_id"].as_integer() == user_id)
   
    if attribute is not None:
        for attr in attribute:
            if ":" not in attr:
                raise HTTPException(
                    status_code=400,
                    detail="Attribute filter must use the format key:value",
                )

            key, value = attr.split(":", 1)

            if not key or not value:
                raise HTTPException(
                    status_code=400,
                    detail="Attribute filter key and value cannot be empty",
                )

            query = query.filter(
                Log.attributes.has_key(key),
                Log.attributes[key].as_string() == value,
            )

    if start_time is not None:
        query = query.filter(Log.timestamp >= start_time)

    if end_time is not None:
        query = query.filter(Log.timestamp <= end_time)

    if sort == "asc":
        query = query.order_by(Log.timestamp.asc())
    else:
        query = query.order_by(Log.timestamp.desc())

    logs = (
        query
        .limit(limit)
        .offset(offset)
        .all()
    )
    return logs

@app.get("/logs/aggregate")
def get_logs_aggregate(
    since: datetime,
    until: datetime,
    bucket: str = Query(
        default="1h",
        pattern="^(1m|5m|1h|1d)$",
    ),
    group_by: str | None = Query(
        default=None,
        pattern="^(service|level)$",
    ),
    db: Session = Depends(get_db),
):
    if since > until:
        raise HTTPException(
            status_code=400,
            detail="since must be earlier than or equal to until",
        )

    bucket_seconds = {
        "1m": 60,
        "5m": 300,
        "1h": 3600,
        "1d": 86400,
    }

    seconds = bucket_seconds[bucket]

    bucket_start = func.date_bin(
        timedelta(seconds=seconds),
        Log.timestamp,
        since,
    )

    query = (
        db.query(
            bucket_start.label("bucket"),
            func.count(Log.id).label("count"),
        )
        .filter(
            Log.timestamp >= since,
            Log.timestamp <= until,
        )
    )

    if group_by == "service":
        query = query.add_columns(Log.service)
        query = query.group_by(bucket_start, Log.service)
        query = query.order_by(bucket_start.asc(), Log.service.asc())

    elif group_by == "level":
        query = query.add_columns(Log.level)
        query = query.group_by(bucket_start, Log.level)
        query = query.order_by(bucket_start.asc(), Log.level.asc())

    else:
        query = query.group_by(bucket_start)
        query = query.order_by(bucket_start.asc())

    results = query.all()

    buckets = []

    for row in results:
        if group_by == "service":
            buckets.append({
                "timestamp": row.bucket,
                "service": row.service,
                "count": row.count,
            })

        elif group_by == "level":
            buckets.append({
                "timestamp": row.bucket,
                "level": row.level,
                "count": row.count,
            })

        else:
            buckets.append({
                "timestamp": row.bucket,
                "count": row.count,
            })

    return {
        "buckets": buckets,
    }

@app.get("/logs/stats")
def get_log_stats(
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    db: Session = Depends(get_db),
):

    if start_time is not None and end_time is not None:
        if start_time > end_time:
            raise HTTPException(
                status_code=400,
                detail="start_time must be earlier than or equal to end_time",
            )
    query = db.query(Log)

    if start_time is not None:
        query = query.filter(Log.timestamp >= start_time)

    if end_time is not None:
        query = query.filter(Log.timestamp <= end_time)

    stats = (
        query.with_entities(
            Log.level,
            func.count(Log.id)
        )
        .group_by(Log.level)
        .all()
    )

    service_stats = (
        query.with_entities(
            Log.service,
            func.count(Log.id)
        )
        .group_by(Log.service)
        .all()
    )

    total = sum(count for _, count in stats)

    return {
        "total": total,
        "by_level": {
            level: count
            for level, count in stats
        },
        "by_service": {
            service: count
            for service, count in service_stats
        },
    }

@app.get("/logs/{log_id}", response_model=LogResponse)
def get_log(
    log_id: int,
    db: Session = Depends(get_db)
 ):
    log = db.query(Log).filter(Log.id == log_id).first()

    if log is None:
        raise HTTPException(status_code=404, detail="Log not found")

    return log


@app.delete("/logs/retention")
def delete_old_logs(
    days: int = Query(default=30, ge=1 , le=3650),
    db: Session = Depends(get_db),
):
    cutoff_time = datetime.now().astimezone() - timedelta(days=days)

    deleted_count = (
        db.query(Log)
        .filter(Log.timestamp < cutoff_time)
        .delete(synchronize_session=False)
    )

    db.commit()

    return {
        "deleted": deleted_count,
        "message": f"Deleted logs older than {days} days",
    }

@app.delete("/logs/{log_id}")
def delete_log(
    log_id: int,
    db: Session = Depends(get_db),
):
    log = db.query(Log).filter(Log.id == log_id).first()

    if log is None:
        raise HTTPException(
            status_code=404,
            detail="Log not found",
        )

    db.delete(log)
    db.commit()

    return {
        "message": "Log deleted successfully",
        "id": log_id,
    }
    

@app.get("/health")
def health():
    return {"status": "ok"}
