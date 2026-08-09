"""
Migrate old BOM JSON export data to the new database schema.

Old format:
  - Simple indicator exports: {code: {name, min, max, unit, ...}}
  - BOM exports: {test_item_key: {item_name, station, indicators: [{ind_key: {code, name, min, max, unit, params, test_params}}]}}

New schema:
  - indicator_dict: code, name, category, domain, unit, test_rule, params, ...
  - test_item_collection: name, code, product_type, ...
  - collection_test_item: collection_id, name, station, test_type, ...
  - test_item_indicator: test_item_id, indicator_id, unit, judgment_rule
  - bom_config: bom_code, bom_name, collection_id, ...
  - bom_indicator: bom_config_id, indicator_id, unit
"""
import asyncio
import json
import os
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.metrics import (
    IndicatorDict, BomConfig, BomIndicator, TestItemCollection,
    CollectionTestItem, TestItemIndicator,
)

SCRIPT_EXPORTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'uploads', 'script_exports')


def get_domain_from_name(name_or_code):
    s = (name_or_code or '').lower()
    if 'tx' in s:
        return 'fd'
    elif 'rx' in s:
        return 'algorithm'
    elif 'trx' in s:
        return 'trx'
    elif 'pwr' in s or 'power' in s:
        return 'power'
    elif 'board' in s:
        return 'board_software'
    elif 'ict' in s:
        return 'ict'
    return None


def get_category_from_name(name):
    name_lower = (name or '').lower()
    if 'voltage' in name_lower or 'vot' in name_lower:
        return 'electrical'
    elif 'freq' in name_lower:
        return 'rf'
    elif 'temp' in name_lower:
        return 'environment'
    elif 'noise' in name_lower:
        return 'acoustic'
    elif 'digital' in name_lower:
        return 'digital'
    elif 'version' in name_lower:
        return 'version'
    return 'general'


async def get_or_create_indicator(session, code, ind_data):
    result = await session.execute(
        select(IndicatorDict).where(IndicatorDict.code == code)
    )
    indicator = result.scalar_one_or_none()
    if indicator:
        return indicator

    test_rule = None
    if ind_data.get('min') is not None or ind_data.get('max') is not None:
        test_rule = f"min={ind_data.get('min')}, max={ind_data.get('max')}"

    indicator = IndicatorDict(
        code=code,
        name=ind_data.get('name', code),
        category=get_category_from_name(ind_data.get('name', '')),
        domain=get_domain_from_name(code),
        unit=ind_data.get('unit', ''),
        test_rule=test_rule,
        params=ind_data.get('params', {}),
        test_params=ind_data.get('test_params', []),
        description=ind_data.get('description', ''),
        status=1,
    )
    session.add(indicator)
    await session.flush()
    return indicator


async def migrate_indicator_dict(session, data):
    """Migrate simple indicator dictionary exports."""
    imported = 0
    for key, value in data.items():
        if not isinstance(value, dict) or 'code' not in value:
            continue
        code = value['code']
        indicator = await get_or_create_indicator(session, code, value)
        if indicator:
            imported += 1
    return imported


async def migrate_bom_export(session, filename, data):
    """Migrate BOM export files with test items and indicators."""
    bom_code = filename.replace('.json', '')

    existing = await session.execute(
        select(BomConfig).where(BomConfig.bom_code == bom_code)
    )
    if existing.scalar_one_or_none():
        print(f"  Skipping (already exists): {bom_code}")
        return 0

    # Create a TestItemCollection for this BOM
    collection = TestItemCollection(
        name=bom_code,
        code=f"COL_{bom_code}",
        product_type='migrated',
        description=f'Migrated from {filename}',
        status=1,
        version=1,
    )
    session.add(collection)
    await session.flush()

    imported_indicators = 0

    # Process each top-level key as a test item
    for item_key, item_data in data.items():
        if not isinstance(item_data, dict):
            continue

        item_name = item_data.get('item_name', item_key) or item_key
        station = item_data.get('station', '')
        test_type = item_data.get('test_type', '')
        indicators = item_data.get('indicators', [])

        # Create CollectionTestItem
        collection_item = CollectionTestItem(
            collection_id=collection.id,
            name=item_name,
            station=station,
            process_name=test_type,
            test_type=test_type,
        )
        session.add(collection_item)
        await session.flush()

        # Process indicators within this test item
        for ind_wrapper in indicators:
            if not isinstance(ind_wrapper, dict):
                continue
            for ind_key, ind_data in ind_wrapper.items():
                if not isinstance(ind_data, dict) or 'code' not in ind_data:
                    continue
                indicator = await get_or_create_indicator(session, ind_data['code'], ind_data)
                imported_indicators += 1

                # Create TestItemIndicator link
                ti_indicator = TestItemIndicator(
                    test_item_id=collection_item.id,
                    indicator_id=indicator.id,
                    unit=ind_data.get('unit', ''),
                )
                session.add(ti_indicator)

    # Create BOM config linked to the collection
    bom = BomConfig(
        bom_code=bom_code,
        bom_name=bom_code,
        collection_id=collection.id,
        collection_version=1,
        status=0,
        version=1,
        review_status='unreviewed',
        domain_owners={},
    )
    session.add(bom)
    await session.flush()

    return imported_indicators


async def migrate_all():
    async with AsyncSessionLocal() as session:
        export_files = []
        if os.path.exists(SCRIPT_EXPORTS_DIR):
            for f in sorted(os.listdir(SCRIPT_EXPORTS_DIR)):
                if f.endswith('.json'):
                    filepath = os.path.join(SCRIPT_EXPORTS_DIR, f)
                    export_files.append(filepath)

        print(f"Found {len(export_files)} export files")

        total_indicators = 0
        total_boms = 0
        total_collections = 0

        for filepath in export_files:
            filename = os.path.basename(filepath)
            with open(filepath) as f:
                data = json.load(f)

            if not data:
                continue

            first_value = next(iter(data.values()), None)
            if isinstance(first_value, dict) and 'indicators' in first_value:
                print(f"\nProcessing BOM: {filename}")
                count = await migrate_bom_export(session, filename, data)
                if count:
                    total_boms += 1
                    total_indicators += count
                    total_collections += 1
                    print(f"  Created BOM with {count} indicators")
            else:
                print(f"\nProcessing indicators: {filename}")
                count = await migrate_indicator_dict(session, data)
                total_indicators += count
                if count:
                    print(f"  Imported {count} indicators")

            await session.commit()

        print(f"\n{'='*50}")
        print(f"Migration complete:")
        print(f"  Collections created: {total_collections}")
        print(f"  BOMs created: {total_boms}")
        print(f"  Total indicators processed: {total_indicators}")
        print(f"{'='*50}")


if __name__ == "__main__":
    asyncio.run(migrate_all())
