package analytics

import (
	"context"
	"database/sql"
	"encoding/json"
	"time"

	"github.com/ClickHouse/clickhouse-go/v2"
	"github.com/sirupsen/logrus"

	"papaya-backend/internal/config"
)

const insertUserEventSQL = `
	INSERT INTO user_events
		(user_id, event_type, entity_type, entity_id, thread_id, metadata, created_at)
	VALUES
		(?, ?, ?, ?, ?, ?, ?)
`

var defaultRecorder *Recorder

type Recorder struct {
	db *sql.DB
}

func InitClickHouse(cfg config.ClickHouseConfig) (func(), error) {
	if !cfg.Enabled {
		logrus.Info("ClickHouse analytics disabled")
		defaultRecorder = nil
		return func() {}, nil
	}

	db := clickhouse.OpenDB(&clickhouse.Options{
		Addr: []string{cfg.Address},
		Auth: clickhouse.Auth{
			Database: cfg.Database,
			Username: cfg.Username,
			Password: cfg.Password,
		},
		DialTimeout:     5 * time.Second,
		MaxOpenConns:    5,
		MaxIdleConns:    2,
		ConnMaxLifetime: time.Hour,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := db.PingContext(ctx); err != nil {
		_ = db.Close()
		defaultRecorder = nil
		return func() {
		}, err
	}

	defaultRecorder = &Recorder{db: db}
	logrus.Info("Successfully connected to ClickHouse analytics")
	return func() {
		_ = db.Close()
	}, nil
}

func Record(ctx context.Context, event Event) {
	if defaultRecorder == nil {
		return
	}

	defaultRecorder.Record(ctx, event)
}

func (r *Recorder) Record(ctx context.Context, event Event) {
	if r == nil || r.db == nil {
		return
	}

	metadata := "{}"
	if len(event.Metadata) > 0 {
		raw, err := json.Marshal(event.Metadata)
		if err != nil {
			logrus.WithError(err).Warn("failed to marshal analytics event metadata")
		} else {
			metadata = string(raw)
		}
	}

	writeCtx, cancel := context.WithTimeout(ctx, 2*time.Second)
	defer cancel()

	if _, err := r.db.ExecContext(
		writeCtx,
		insertUserEventSQL,
		event.UserID.String(),
		event.EventType,
		event.EntityType,
		event.EntityID.String(),
		event.ThreadID.String(),
		metadata,
		time.Now().UTC(),
	); err != nil {
		logrus.WithError(err).WithFields(logrus.Fields{
			"event_type":  event.EventType,
			"entity_type": event.EntityType,
			"entity_id":   event.EntityID.String(),
			"thread_id":   event.ThreadID.String(),
			"user_id":     event.UserID.String(),
		}).Warn("failed to write analytics event")
	}
}
