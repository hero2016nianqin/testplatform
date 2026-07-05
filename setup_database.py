#!/usr/bin/env python3
"""
Simple database setup script for test_platform.
This creates the necessary tables if they don't exist.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db
from app.models.version import TestVersion, VersionArchiveItem, ReleaseStep, ReleaseDeployment, VersionBinaryFile
from app.models.station import TestStation, EquipmentMetrics, EquipmentPropertyPage, SoftwareConfig
from app.models.test_sequence import TestSequence, TestSequenceStep

app = create_app()

with app.app_context():
    print("Creating database tables if they don't exist...")
    db.create_all()
    print("Database tables created successfully!")
