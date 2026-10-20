-- ====================================================================
-- Digital Twin Challenge 2026 - Database Schema
-- Database: digital_twin_db
-- ====================================================================

CREATE DATABASE IF NOT EXISTS `digital_twin_db` 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE `digital_twin_db`;

-- 1. Patients Table (Synthea EHR Demographics & Identification)
CREATE TABLE IF NOT EXISTS `patients` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `patient_uuid` VARCHAR(64) NOT NULL UNIQUE COMMENT 'Unique UUID from Synthea C-CDA record',
    `first_name` VARCHAR(100) NOT NULL,
    `last_name` VARCHAR(100) NOT NULL,
    `gender` VARCHAR(10) NOT NULL COMMENT 'M, F, UN',
    `birth_date` DATE NULL,
    `ethnicity` VARCHAR(50) NULL,
    `race` VARCHAR(50) NULL,
    `city` VARCHAR(100) NULL,
    `state` VARCHAR(50) NULL,
    `source_file` VARCHAR(255) NULL COMMENT 'Original XML file name',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_patient_name` (`last_name`, `first_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Conditions Table (Medical History from Synthea C-CDA)
CREATE TABLE IF NOT EXISTS `conditions` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `patient_id` INT NOT NULL,
    `code` VARCHAR(100) NULL COMMENT 'SNOMED-CT or other medical coding',
    `display_name` VARCHAR(255) NOT NULL COMMENT 'Clinical name of condition',
    `code_system` VARCHAR(100) DEFAULT 'SNOMED-CT',
    `onset_date` VARCHAR(50) NULL,
    `resolved_date` VARCHAR(50) NULL,
    `status` VARCHAR(50) DEFAULT 'active',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_condition_patient` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE,
    CONSTRAINT `uq_patient_condition` UNIQUE KEY (`patient_id`, `code`(50), `onset_date`(30)),
    INDEX `idx_condition_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Medications Table (Prescription History from Synthea)
CREATE TABLE IF NOT EXISTS `medications` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `patient_id` INT NOT NULL,
    `medication_name` VARCHAR(255) NOT NULL,
    `rxnorm_code` VARCHAR(100) NULL,
    `start_date` VARCHAR(50) NULL,
    `stop_date` VARCHAR(50) NULL,
    `status` VARCHAR(50) DEFAULT 'active',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_medication_patient` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE,
    CONSTRAINT `uq_patient_medication` UNIQUE KEY (`patient_id`, `medication_name`(100), `start_date`(30))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Twin Profiles Table (The In-Silico Digital Twin Entity)
CREATE TABLE IF NOT EXISTS `twin_profiles` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `patient_id` INT NOT NULL UNIQUE COMMENT 'Core EHR patient representation',
    `twin_name` VARCHAR(150) NOT NULL,
    `twin_status` VARCHAR(50) DEFAULT 'active' COMMENT 'active, calibrating, paused, offline',
    `baseline_hba1c` DECIMAL(4,2) NULL,
    `target_glucose_min` DECIMAL(5,2) DEFAULT 70.00 COMMENT 'Lower ADA target boundary (mg/dL)',
    `target_glucose_max` DECIMAL(5,2) DEFAULT 180.00 COMMENT 'Upper ADA target boundary (mg/dL)',
    `insulin_sensitivity` DECIMAL(5,2) NULL COMMENT 'ISF (mg/dL per unit)',
    `carb_ratio` DECIMAL(5,2) NULL COMMENT 'Carb-to-insulin ratio (g/U)',
    `paired_device_type` VARCHAR(100) DEFAULT 'CGM+Wearable',
    `paired_cgm_user_id` VARCHAR(50) NULL COMMENT 'Kaggle GlucoBench subject pairing (e.g. U001)',
    `paired_wearable_subject_id` VARCHAR(50) NULL COMMENT 'Wearable dataset subject pairing (e.g. S01)',
    `last_sync_time` DATETIME NULL,
    `risk_level` VARCHAR(50) DEFAULT 'normal' COMMENT 'normal, elevated, high, critical',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_twin_patient` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE,
    INDEX `idx_twin_cgm_user` (`paired_cgm_user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Glucose Readings Table (High-Frequency CGM & Physiological Stream from GlucoBench)
CREATE TABLE IF NOT EXISTS `glucose_readings` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `twin_id` INT NULL COMMENT 'Linked Digital Twin profile if paired',
    `cgm_user_id` VARCHAR(50) NOT NULL COMMENT 'Raw Kaggle GlucoBench user_id (U001 - U010)',
    `recorded_at` DATETIME NOT NULL,
    `glucose_level` DECIMAL(5,2) NOT NULL COMMENT 'CGM reading in mg/dL',
    `cgm_quality_flag` TINYINT DEFAULT 1 COMMENT '1 = valid, 0 = sensor noisy/error',
    `insulin_bolus` DECIMAL(5,2) DEFAULT 0.00 COMMENT 'Bolus units (U)',
    `insulin_basal` DECIMAL(5,2) DEFAULT 0.00 COMMENT 'Basal rate (U/h)',
    `carbs` INT DEFAULT 0 COMMENT 'Grams of carbohydrates',
    `meal_type` VARCHAR(30) DEFAULT 'none',
    `exercise_steps` INT DEFAULT 0,
    `exercise_intensity` VARCHAR(30) DEFAULT 'none',
    `heart_rate` DECIMAL(5,2) NULL COMMENT 'Sensor BPM',
    `skin_temp` DECIMAL(5,2) NULL COMMENT 'Skin temperature (Celsius)',
    `gsr` DECIMAL(6,3) NULL COMMENT 'Galvanic skin response (microsiemens)',
    `sleep_stage` VARCHAR(30) DEFAULT 'awake',
    `medication_other` VARCHAR(50) DEFAULT 'none',
    `stress_level` TINYINT DEFAULT 0,
    `alcohol` DECIMAL(5,2) DEFAULT 0.00,
    `device_id` VARCHAR(50) NULL,
    `glucose_lag_1` DECIMAL(5,2) NULL,
    `glucose_lag_3` DECIMAL(5,2) NULL,
    `glucose_lag_6` DECIMAL(5,2) NULL,
    `glucose_roll_mean_1h` DECIMAL(5,2) NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_glucose_twin` FOREIGN KEY (`twin_id`) REFERENCES `twin_profiles` (`id`) ON DELETE SET NULL,
    CONSTRAINT `uq_cgm_reading` UNIQUE KEY (`cgm_user_id`, `recorded_at`),
    INDEX `idx_cgm_time` (`cgm_user_id`, `recorded_at`),
    INDEX `idx_twin_time` (`twin_id`, `recorded_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
