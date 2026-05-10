package storage

import (
	"fmt"
	"os"
	"vkid-backend/internal/storage/models"

	_ "github.com/lib/pq"
	"github.com/sirupsen/logrus"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
	"gorm.io/gorm/schema"
)

// DB Initialize GORM DB
var DB *gorm.DB

func InitStorage() {
	// Get PostgreSQL connection params
	user := os.Getenv("POSTGRES_USER")
	password := os.Getenv("POSTGRES_PASSWORD")
	dbname := os.Getenv("POSTGRES_DB")
	dbhost := os.Getenv("POSTGRES_HOST")
	port := os.Getenv("PG_PORT")

	dsn := fmt.Sprintf("host=%s user=%s password=%s dbname=%s port=%s sslmode=disable",
		dbhost, user, password, dbname, port)

	var err error
	DB, err = gorm.Open(postgres.Open(dsn), &gorm.Config{
		NamingStrategy: schema.NamingStrategy{
			SingularTable: false,
		},
		Logger: logger.Default.LogMode(logger.Info),
	})
	if err != nil {
		logrus.Fatalf("Failed to connect to database: %v", err)
	}

	logrus.Info("Successfully connected to database!")

	// Auto-migrate all models
	err = DB.AutoMigrate(
		&models.Role{},
		&models.User{},
		&models.Thread{},
		&models.Post{},
		&models.Attachment{},
		&models.Comment{},
		&models.Like{})
	if err != nil {
		logrus.Fatalf("Failed to migrate database tables: %v", err)
	}

	// Create pg_trgm extension if it doesn't exist
	err = DB.Exec("CREATE EXTENSION IF NOT EXISTS pg_trgm;").Error
	if err != nil {
		logrus.Fatalf("Failed to create pg_trgm extension: %v", err)
	}

	// Create index using pg_trgm for the title column
	err = DB.Exec("CREATE INDEX IF NOT EXISTS idx_title_trgm ON threads USING gin (title gin_trgm_ops);").Error
	if err != nil {
		logrus.Fatalf("Failed to create index on title: %v", err)
	}
}
