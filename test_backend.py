import backend.database as db

def main():
    print('Initializing DB')
    db.init_db()
    df = db.read_complaints_df()
    print('Initial rows', len(df))
    # Insert a new complaint
    record = {
        'created_date': '2023-01-01',
        'area': 'Test Area',
        'category': 'Test',
        'status': 'Pending',
        'description': 'Test description',
    }
    new = db.insert_complaint(record)
    print('Inserted', new)
    fetched = db.get_complaint_by_id(new['id'])
    print('Fetched', fetched)
    updated = db.update_complaint_record(new['id'], {'status': 'Closed', 'closed_date': '2023-01-02'})
    print('Updated', updated)
    db.delete_complaint_record(new['id'])
    print('Deleted')
    print('After delete rows', len(db.read_complaints_df()))

if __name__ == '__main__':
    main()
