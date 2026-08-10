// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'work_order_database.dart';

// ignore_for_file: type=lint
class $CachedWorkOrdersTable extends CachedWorkOrders
    with TableInfo<$CachedWorkOrdersTable, CachedWorkOrder> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $CachedWorkOrdersTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
      'id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _codeMeta = const VerificationMeta('code');
  @override
  late final GeneratedColumn<String> code = GeneratedColumn<String>(
      'code', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _customerNameMeta =
      const VerificationMeta('customerName');
  @override
  late final GeneratedColumn<String> customerName = GeneratedColumn<String>(
      'customer_name', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _addressMeta =
      const VerificationMeta('address');
  @override
  late final GeneratedColumn<String> address = GeneratedColumn<String>(
      'address', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _statusMeta = const VerificationMeta('status');
  @override
  late final GeneratedColumn<String> status = GeneratedColumn<String>(
      'status', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _versionMeta =
      const VerificationMeta('version');
  @override
  late final GeneratedColumn<int> version = GeneratedColumn<int>(
      'version', aliasedName, false,
      type: DriftSqlType.int, requiredDuringInsert: true);
  static const VerificationMeta _latitudeMeta =
      const VerificationMeta('latitude');
  @override
  late final GeneratedColumn<double> latitude = GeneratedColumn<double>(
      'latitude', aliasedName, true,
      type: DriftSqlType.double, requiredDuringInsert: false);
  static const VerificationMeta _longitudeMeta =
      const VerificationMeta('longitude');
  @override
  late final GeneratedColumn<double> longitude = GeneratedColumn<double>(
      'longitude', aliasedName, true,
      type: DriftSqlType.double, requiredDuringInsert: false);
  static const VerificationMeta _priorityMeta =
      const VerificationMeta('priority');
  @override
  late final GeneratedColumn<String> priority = GeneratedColumn<String>(
      'priority', aliasedName, false,
      type: DriftSqlType.string,
      requiredDuringInsert: false,
      defaultValue: const Constant('normal'));
  static const VerificationMeta _scheduledAtMeta =
      const VerificationMeta('scheduledAt');
  @override
  late final GeneratedColumn<DateTime> scheduledAt = GeneratedColumn<DateTime>(
      'scheduled_at', aliasedName, true,
      type: DriftSqlType.dateTime, requiredDuringInsert: false);
  static const VerificationMeta _updatedAtMeta =
      const VerificationMeta('updatedAt');
  @override
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
      'updated_at', aliasedName, false,
      type: DriftSqlType.dateTime, requiredDuringInsert: true);
  @override
  List<GeneratedColumn> get $columns => [
        id,
        code,
        customerName,
        address,
        status,
        version,
        latitude,
        longitude,
        priority,
        scheduledAt,
        updatedAt
      ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'cached_work_orders';
  @override
  VerificationContext validateIntegrity(Insertable<CachedWorkOrder> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('code')) {
      context.handle(
          _codeMeta, code.isAcceptableOrUnknown(data['code']!, _codeMeta));
    } else if (isInserting) {
      context.missing(_codeMeta);
    }
    if (data.containsKey('customer_name')) {
      context.handle(
          _customerNameMeta,
          customerName.isAcceptableOrUnknown(
              data['customer_name']!, _customerNameMeta));
    } else if (isInserting) {
      context.missing(_customerNameMeta);
    }
    if (data.containsKey('address')) {
      context.handle(_addressMeta,
          address.isAcceptableOrUnknown(data['address']!, _addressMeta));
    } else if (isInserting) {
      context.missing(_addressMeta);
    }
    if (data.containsKey('status')) {
      context.handle(_statusMeta,
          status.isAcceptableOrUnknown(data['status']!, _statusMeta));
    } else if (isInserting) {
      context.missing(_statusMeta);
    }
    if (data.containsKey('version')) {
      context.handle(_versionMeta,
          version.isAcceptableOrUnknown(data['version']!, _versionMeta));
    } else if (isInserting) {
      context.missing(_versionMeta);
    }
    if (data.containsKey('latitude')) {
      context.handle(_latitudeMeta,
          latitude.isAcceptableOrUnknown(data['latitude']!, _latitudeMeta));
    }
    if (data.containsKey('longitude')) {
      context.handle(_longitudeMeta,
          longitude.isAcceptableOrUnknown(data['longitude']!, _longitudeMeta));
    }
    if (data.containsKey('priority')) {
      context.handle(_priorityMeta,
          priority.isAcceptableOrUnknown(data['priority']!, _priorityMeta));
    }
    if (data.containsKey('scheduled_at')) {
      context.handle(
          _scheduledAtMeta,
          scheduledAt.isAcceptableOrUnknown(
              data['scheduled_at']!, _scheduledAtMeta));
    }
    if (data.containsKey('updated_at')) {
      context.handle(_updatedAtMeta,
          updatedAt.isAcceptableOrUnknown(data['updated_at']!, _updatedAtMeta));
    } else if (isInserting) {
      context.missing(_updatedAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  CachedWorkOrder map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return CachedWorkOrder(
      id: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      code: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}code'])!,
      customerName: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}customer_name'])!,
      address: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}address'])!,
      status: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}status'])!,
      version: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}version'])!,
      latitude: attachedDatabase.typeMapping
          .read(DriftSqlType.double, data['${effectivePrefix}latitude']),
      longitude: attachedDatabase.typeMapping
          .read(DriftSqlType.double, data['${effectivePrefix}longitude']),
      priority: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}priority'])!,
      scheduledAt: attachedDatabase.typeMapping
          .read(DriftSqlType.dateTime, data['${effectivePrefix}scheduled_at']),
      updatedAt: attachedDatabase.typeMapping
          .read(DriftSqlType.dateTime, data['${effectivePrefix}updated_at'])!,
    );
  }

  @override
  $CachedWorkOrdersTable createAlias(String alias) {
    return $CachedWorkOrdersTable(attachedDatabase, alias);
  }
}

class CachedWorkOrder extends DataClass implements Insertable<CachedWorkOrder> {
  final String id;
  final String code;
  final String customerName;
  final String address;
  final String status;
  final int version;
  final double? latitude;
  final double? longitude;
  final String priority;
  final DateTime? scheduledAt;
  final DateTime updatedAt;
  const CachedWorkOrder(
      {required this.id,
      required this.code,
      required this.customerName,
      required this.address,
      required this.status,
      required this.version,
      this.latitude,
      this.longitude,
      required this.priority,
      this.scheduledAt,
      required this.updatedAt});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['code'] = Variable<String>(code);
    map['customer_name'] = Variable<String>(customerName);
    map['address'] = Variable<String>(address);
    map['status'] = Variable<String>(status);
    map['version'] = Variable<int>(version);
    if (!nullToAbsent || latitude != null) {
      map['latitude'] = Variable<double>(latitude);
    }
    if (!nullToAbsent || longitude != null) {
      map['longitude'] = Variable<double>(longitude);
    }
    map['priority'] = Variable<String>(priority);
    if (!nullToAbsent || scheduledAt != null) {
      map['scheduled_at'] = Variable<DateTime>(scheduledAt);
    }
    map['updated_at'] = Variable<DateTime>(updatedAt);
    return map;
  }

  CachedWorkOrdersCompanion toCompanion(bool nullToAbsent) {
    return CachedWorkOrdersCompanion(
      id: Value(id),
      code: Value(code),
      customerName: Value(customerName),
      address: Value(address),
      status: Value(status),
      version: Value(version),
      latitude: latitude == null && nullToAbsent
          ? const Value.absent()
          : Value(latitude),
      longitude: longitude == null && nullToAbsent
          ? const Value.absent()
          : Value(longitude),
      priority: Value(priority),
      scheduledAt: scheduledAt == null && nullToAbsent
          ? const Value.absent()
          : Value(scheduledAt),
      updatedAt: Value(updatedAt),
    );
  }

  factory CachedWorkOrder.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return CachedWorkOrder(
      id: serializer.fromJson<String>(json['id']),
      code: serializer.fromJson<String>(json['code']),
      customerName: serializer.fromJson<String>(json['customerName']),
      address: serializer.fromJson<String>(json['address']),
      status: serializer.fromJson<String>(json['status']),
      version: serializer.fromJson<int>(json['version']),
      latitude: serializer.fromJson<double?>(json['latitude']),
      longitude: serializer.fromJson<double?>(json['longitude']),
      priority: serializer.fromJson<String>(json['priority']),
      scheduledAt: serializer.fromJson<DateTime?>(json['scheduledAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'code': serializer.toJson<String>(code),
      'customerName': serializer.toJson<String>(customerName),
      'address': serializer.toJson<String>(address),
      'status': serializer.toJson<String>(status),
      'version': serializer.toJson<int>(version),
      'latitude': serializer.toJson<double?>(latitude),
      'longitude': serializer.toJson<double?>(longitude),
      'priority': serializer.toJson<String>(priority),
      'scheduledAt': serializer.toJson<DateTime?>(scheduledAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
    };
  }

  CachedWorkOrder copyWith(
          {String? id,
          String? code,
          String? customerName,
          String? address,
          String? status,
          int? version,
          Value<double?> latitude = const Value.absent(),
          Value<double?> longitude = const Value.absent(),
          String? priority,
          Value<DateTime?> scheduledAt = const Value.absent(),
          DateTime? updatedAt}) =>
      CachedWorkOrder(
        id: id ?? this.id,
        code: code ?? this.code,
        customerName: customerName ?? this.customerName,
        address: address ?? this.address,
        status: status ?? this.status,
        version: version ?? this.version,
        latitude: latitude.present ? latitude.value : this.latitude,
        longitude: longitude.present ? longitude.value : this.longitude,
        priority: priority ?? this.priority,
        scheduledAt: scheduledAt.present ? scheduledAt.value : this.scheduledAt,
        updatedAt: updatedAt ?? this.updatedAt,
      );
  CachedWorkOrder copyWithCompanion(CachedWorkOrdersCompanion data) {
    return CachedWorkOrder(
      id: data.id.present ? data.id.value : this.id,
      code: data.code.present ? data.code.value : this.code,
      customerName: data.customerName.present
          ? data.customerName.value
          : this.customerName,
      address: data.address.present ? data.address.value : this.address,
      status: data.status.present ? data.status.value : this.status,
      version: data.version.present ? data.version.value : this.version,
      latitude: data.latitude.present ? data.latitude.value : this.latitude,
      longitude: data.longitude.present ? data.longitude.value : this.longitude,
      priority: data.priority.present ? data.priority.value : this.priority,
      scheduledAt:
          data.scheduledAt.present ? data.scheduledAt.value : this.scheduledAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('CachedWorkOrder(')
          ..write('id: $id, ')
          ..write('code: $code, ')
          ..write('customerName: $customerName, ')
          ..write('address: $address, ')
          ..write('status: $status, ')
          ..write('version: $version, ')
          ..write('latitude: $latitude, ')
          ..write('longitude: $longitude, ')
          ..write('priority: $priority, ')
          ..write('scheduledAt: $scheduledAt, ')
          ..write('updatedAt: $updatedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(id, code, customerName, address, status,
      version, latitude, longitude, priority, scheduledAt, updatedAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is CachedWorkOrder &&
          other.id == this.id &&
          other.code == this.code &&
          other.customerName == this.customerName &&
          other.address == this.address &&
          other.status == this.status &&
          other.version == this.version &&
          other.latitude == this.latitude &&
          other.longitude == this.longitude &&
          other.priority == this.priority &&
          other.scheduledAt == this.scheduledAt &&
          other.updatedAt == this.updatedAt);
}

class CachedWorkOrdersCompanion extends UpdateCompanion<CachedWorkOrder> {
  final Value<String> id;
  final Value<String> code;
  final Value<String> customerName;
  final Value<String> address;
  final Value<String> status;
  final Value<int> version;
  final Value<double?> latitude;
  final Value<double?> longitude;
  final Value<String> priority;
  final Value<DateTime?> scheduledAt;
  final Value<DateTime> updatedAt;
  final Value<int> rowid;
  const CachedWorkOrdersCompanion({
    this.id = const Value.absent(),
    this.code = const Value.absent(),
    this.customerName = const Value.absent(),
    this.address = const Value.absent(),
    this.status = const Value.absent(),
    this.version = const Value.absent(),
    this.latitude = const Value.absent(),
    this.longitude = const Value.absent(),
    this.priority = const Value.absent(),
    this.scheduledAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  CachedWorkOrdersCompanion.insert({
    required String id,
    required String code,
    required String customerName,
    required String address,
    required String status,
    required int version,
    this.latitude = const Value.absent(),
    this.longitude = const Value.absent(),
    this.priority = const Value.absent(),
    this.scheduledAt = const Value.absent(),
    required DateTime updatedAt,
    this.rowid = const Value.absent(),
  })  : id = Value(id),
        code = Value(code),
        customerName = Value(customerName),
        address = Value(address),
        status = Value(status),
        version = Value(version),
        updatedAt = Value(updatedAt);
  static Insertable<CachedWorkOrder> custom({
    Expression<String>? id,
    Expression<String>? code,
    Expression<String>? customerName,
    Expression<String>? address,
    Expression<String>? status,
    Expression<int>? version,
    Expression<double>? latitude,
    Expression<double>? longitude,
    Expression<String>? priority,
    Expression<DateTime>? scheduledAt,
    Expression<DateTime>? updatedAt,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (code != null) 'code': code,
      if (customerName != null) 'customer_name': customerName,
      if (address != null) 'address': address,
      if (status != null) 'status': status,
      if (version != null) 'version': version,
      if (latitude != null) 'latitude': latitude,
      if (longitude != null) 'longitude': longitude,
      if (priority != null) 'priority': priority,
      if (scheduledAt != null) 'scheduled_at': scheduledAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (rowid != null) 'rowid': rowid,
    });
  }

  CachedWorkOrdersCompanion copyWith(
      {Value<String>? id,
      Value<String>? code,
      Value<String>? customerName,
      Value<String>? address,
      Value<String>? status,
      Value<int>? version,
      Value<double?>? latitude,
      Value<double?>? longitude,
      Value<String>? priority,
      Value<DateTime?>? scheduledAt,
      Value<DateTime>? updatedAt,
      Value<int>? rowid}) {
    return CachedWorkOrdersCompanion(
      id: id ?? this.id,
      code: code ?? this.code,
      customerName: customerName ?? this.customerName,
      address: address ?? this.address,
      status: status ?? this.status,
      version: version ?? this.version,
      latitude: latitude ?? this.latitude,
      longitude: longitude ?? this.longitude,
      priority: priority ?? this.priority,
      scheduledAt: scheduledAt ?? this.scheduledAt,
      updatedAt: updatedAt ?? this.updatedAt,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (code.present) {
      map['code'] = Variable<String>(code.value);
    }
    if (customerName.present) {
      map['customer_name'] = Variable<String>(customerName.value);
    }
    if (address.present) {
      map['address'] = Variable<String>(address.value);
    }
    if (status.present) {
      map['status'] = Variable<String>(status.value);
    }
    if (version.present) {
      map['version'] = Variable<int>(version.value);
    }
    if (latitude.present) {
      map['latitude'] = Variable<double>(latitude.value);
    }
    if (longitude.present) {
      map['longitude'] = Variable<double>(longitude.value);
    }
    if (priority.present) {
      map['priority'] = Variable<String>(priority.value);
    }
    if (scheduledAt.present) {
      map['scheduled_at'] = Variable<DateTime>(scheduledAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('CachedWorkOrdersCompanion(')
          ..write('id: $id, ')
          ..write('code: $code, ')
          ..write('customerName: $customerName, ')
          ..write('address: $address, ')
          ..write('status: $status, ')
          ..write('version: $version, ')
          ..write('latitude: $latitude, ')
          ..write('longitude: $longitude, ')
          ..write('priority: $priority, ')
          ..write('scheduledAt: $scheduledAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $SyncQueueEntriesTable extends SyncQueueEntries
    with TableInfo<$SyncQueueEntriesTable, SyncQueueEntry> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $SyncQueueEntriesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _operationIdMeta =
      const VerificationMeta('operationId');
  @override
  late final GeneratedColumn<String> operationId = GeneratedColumn<String>(
      'operation_id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _entityTypeMeta =
      const VerificationMeta('entityType');
  @override
  late final GeneratedColumn<String> entityType = GeneratedColumn<String>(
      'entity_type', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _entityIdMeta =
      const VerificationMeta('entityId');
  @override
  late final GeneratedColumn<String> entityId = GeneratedColumn<String>(
      'entity_id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _kindMeta = const VerificationMeta('kind');
  @override
  late final GeneratedColumn<String> kind = GeneratedColumn<String>(
      'kind', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _baseVersionMeta =
      const VerificationMeta('baseVersion');
  @override
  late final GeneratedColumn<int> baseVersion = GeneratedColumn<int>(
      'base_version', aliasedName, true,
      type: DriftSqlType.int, requiredDuringInsert: false);
  static const VerificationMeta _occurredAtMeta =
      const VerificationMeta('occurredAt');
  @override
  late final GeneratedColumn<DateTime> occurredAt = GeneratedColumn<DateTime>(
      'occurred_at', aliasedName, false,
      type: DriftSqlType.dateTime, requiredDuringInsert: true);
  static const VerificationMeta _payloadJsonMeta =
      const VerificationMeta('payloadJson');
  @override
  late final GeneratedColumn<String> payloadJson = GeneratedColumn<String>(
      'payload_json', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _stateMeta = const VerificationMeta('state');
  @override
  late final GeneratedColumn<String> state = GeneratedColumn<String>(
      'state', aliasedName, false,
      type: DriftSqlType.string,
      requiredDuringInsert: false,
      defaultValue: const Constant('pending'));
  static const VerificationMeta _attemptsMeta =
      const VerificationMeta('attempts');
  @override
  late final GeneratedColumn<int> attempts = GeneratedColumn<int>(
      'attempts', aliasedName, false,
      type: DriftSqlType.int,
      requiredDuringInsert: false,
      defaultValue: const Constant(0));
  static const VerificationMeta _lastErrorMeta =
      const VerificationMeta('lastError');
  @override
  late final GeneratedColumn<String> lastError = GeneratedColumn<String>(
      'last_error', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  @override
  List<GeneratedColumn> get $columns => [
        operationId,
        entityType,
        entityId,
        kind,
        baseVersion,
        occurredAt,
        payloadJson,
        state,
        attempts,
        lastError
      ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'sync_queue_entries';
  @override
  VerificationContext validateIntegrity(Insertable<SyncQueueEntry> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('operation_id')) {
      context.handle(
          _operationIdMeta,
          operationId.isAcceptableOrUnknown(
              data['operation_id']!, _operationIdMeta));
    } else if (isInserting) {
      context.missing(_operationIdMeta);
    }
    if (data.containsKey('entity_type')) {
      context.handle(
          _entityTypeMeta,
          entityType.isAcceptableOrUnknown(
              data['entity_type']!, _entityTypeMeta));
    } else if (isInserting) {
      context.missing(_entityTypeMeta);
    }
    if (data.containsKey('entity_id')) {
      context.handle(_entityIdMeta,
          entityId.isAcceptableOrUnknown(data['entity_id']!, _entityIdMeta));
    } else if (isInserting) {
      context.missing(_entityIdMeta);
    }
    if (data.containsKey('kind')) {
      context.handle(
          _kindMeta, kind.isAcceptableOrUnknown(data['kind']!, _kindMeta));
    } else if (isInserting) {
      context.missing(_kindMeta);
    }
    if (data.containsKey('base_version')) {
      context.handle(
          _baseVersionMeta,
          baseVersion.isAcceptableOrUnknown(
              data['base_version']!, _baseVersionMeta));
    }
    if (data.containsKey('occurred_at')) {
      context.handle(
          _occurredAtMeta,
          occurredAt.isAcceptableOrUnknown(
              data['occurred_at']!, _occurredAtMeta));
    } else if (isInserting) {
      context.missing(_occurredAtMeta);
    }
    if (data.containsKey('payload_json')) {
      context.handle(
          _payloadJsonMeta,
          payloadJson.isAcceptableOrUnknown(
              data['payload_json']!, _payloadJsonMeta));
    } else if (isInserting) {
      context.missing(_payloadJsonMeta);
    }
    if (data.containsKey('state')) {
      context.handle(
          _stateMeta, state.isAcceptableOrUnknown(data['state']!, _stateMeta));
    }
    if (data.containsKey('attempts')) {
      context.handle(_attemptsMeta,
          attempts.isAcceptableOrUnknown(data['attempts']!, _attemptsMeta));
    }
    if (data.containsKey('last_error')) {
      context.handle(_lastErrorMeta,
          lastError.isAcceptableOrUnknown(data['last_error']!, _lastErrorMeta));
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {operationId};
  @override
  SyncQueueEntry map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return SyncQueueEntry(
      operationId: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}operation_id'])!,
      entityType: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}entity_type'])!,
      entityId: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}entity_id'])!,
      kind: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}kind'])!,
      baseVersion: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}base_version']),
      occurredAt: attachedDatabase.typeMapping
          .read(DriftSqlType.dateTime, data['${effectivePrefix}occurred_at'])!,
      payloadJson: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}payload_json'])!,
      state: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}state'])!,
      attempts: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}attempts'])!,
      lastError: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}last_error']),
    );
  }

  @override
  $SyncQueueEntriesTable createAlias(String alias) {
    return $SyncQueueEntriesTable(attachedDatabase, alias);
  }
}

class SyncQueueEntry extends DataClass implements Insertable<SyncQueueEntry> {
  final String operationId;
  final String entityType;
  final String entityId;
  final String kind;
  final int? baseVersion;
  final DateTime occurredAt;
  final String payloadJson;
  final String state;
  final int attempts;
  final String? lastError;
  const SyncQueueEntry(
      {required this.operationId,
      required this.entityType,
      required this.entityId,
      required this.kind,
      this.baseVersion,
      required this.occurredAt,
      required this.payloadJson,
      required this.state,
      required this.attempts,
      this.lastError});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['operation_id'] = Variable<String>(operationId);
    map['entity_type'] = Variable<String>(entityType);
    map['entity_id'] = Variable<String>(entityId);
    map['kind'] = Variable<String>(kind);
    if (!nullToAbsent || baseVersion != null) {
      map['base_version'] = Variable<int>(baseVersion);
    }
    map['occurred_at'] = Variable<DateTime>(occurredAt);
    map['payload_json'] = Variable<String>(payloadJson);
    map['state'] = Variable<String>(state);
    map['attempts'] = Variable<int>(attempts);
    if (!nullToAbsent || lastError != null) {
      map['last_error'] = Variable<String>(lastError);
    }
    return map;
  }

  SyncQueueEntriesCompanion toCompanion(bool nullToAbsent) {
    return SyncQueueEntriesCompanion(
      operationId: Value(operationId),
      entityType: Value(entityType),
      entityId: Value(entityId),
      kind: Value(kind),
      baseVersion: baseVersion == null && nullToAbsent
          ? const Value.absent()
          : Value(baseVersion),
      occurredAt: Value(occurredAt),
      payloadJson: Value(payloadJson),
      state: Value(state),
      attempts: Value(attempts),
      lastError: lastError == null && nullToAbsent
          ? const Value.absent()
          : Value(lastError),
    );
  }

  factory SyncQueueEntry.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return SyncQueueEntry(
      operationId: serializer.fromJson<String>(json['operationId']),
      entityType: serializer.fromJson<String>(json['entityType']),
      entityId: serializer.fromJson<String>(json['entityId']),
      kind: serializer.fromJson<String>(json['kind']),
      baseVersion: serializer.fromJson<int?>(json['baseVersion']),
      occurredAt: serializer.fromJson<DateTime>(json['occurredAt']),
      payloadJson: serializer.fromJson<String>(json['payloadJson']),
      state: serializer.fromJson<String>(json['state']),
      attempts: serializer.fromJson<int>(json['attempts']),
      lastError: serializer.fromJson<String?>(json['lastError']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'operationId': serializer.toJson<String>(operationId),
      'entityType': serializer.toJson<String>(entityType),
      'entityId': serializer.toJson<String>(entityId),
      'kind': serializer.toJson<String>(kind),
      'baseVersion': serializer.toJson<int?>(baseVersion),
      'occurredAt': serializer.toJson<DateTime>(occurredAt),
      'payloadJson': serializer.toJson<String>(payloadJson),
      'state': serializer.toJson<String>(state),
      'attempts': serializer.toJson<int>(attempts),
      'lastError': serializer.toJson<String?>(lastError),
    };
  }

  SyncQueueEntry copyWith(
          {String? operationId,
          String? entityType,
          String? entityId,
          String? kind,
          Value<int?> baseVersion = const Value.absent(),
          DateTime? occurredAt,
          String? payloadJson,
          String? state,
          int? attempts,
          Value<String?> lastError = const Value.absent()}) =>
      SyncQueueEntry(
        operationId: operationId ?? this.operationId,
        entityType: entityType ?? this.entityType,
        entityId: entityId ?? this.entityId,
        kind: kind ?? this.kind,
        baseVersion: baseVersion.present ? baseVersion.value : this.baseVersion,
        occurredAt: occurredAt ?? this.occurredAt,
        payloadJson: payloadJson ?? this.payloadJson,
        state: state ?? this.state,
        attempts: attempts ?? this.attempts,
        lastError: lastError.present ? lastError.value : this.lastError,
      );
  SyncQueueEntry copyWithCompanion(SyncQueueEntriesCompanion data) {
    return SyncQueueEntry(
      operationId:
          data.operationId.present ? data.operationId.value : this.operationId,
      entityType:
          data.entityType.present ? data.entityType.value : this.entityType,
      entityId: data.entityId.present ? data.entityId.value : this.entityId,
      kind: data.kind.present ? data.kind.value : this.kind,
      baseVersion:
          data.baseVersion.present ? data.baseVersion.value : this.baseVersion,
      occurredAt:
          data.occurredAt.present ? data.occurredAt.value : this.occurredAt,
      payloadJson:
          data.payloadJson.present ? data.payloadJson.value : this.payloadJson,
      state: data.state.present ? data.state.value : this.state,
      attempts: data.attempts.present ? data.attempts.value : this.attempts,
      lastError: data.lastError.present ? data.lastError.value : this.lastError,
    );
  }

  @override
  String toString() {
    return (StringBuffer('SyncQueueEntry(')
          ..write('operationId: $operationId, ')
          ..write('entityType: $entityType, ')
          ..write('entityId: $entityId, ')
          ..write('kind: $kind, ')
          ..write('baseVersion: $baseVersion, ')
          ..write('occurredAt: $occurredAt, ')
          ..write('payloadJson: $payloadJson, ')
          ..write('state: $state, ')
          ..write('attempts: $attempts, ')
          ..write('lastError: $lastError')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(operationId, entityType, entityId, kind,
      baseVersion, occurredAt, payloadJson, state, attempts, lastError);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is SyncQueueEntry &&
          other.operationId == this.operationId &&
          other.entityType == this.entityType &&
          other.entityId == this.entityId &&
          other.kind == this.kind &&
          other.baseVersion == this.baseVersion &&
          other.occurredAt == this.occurredAt &&
          other.payloadJson == this.payloadJson &&
          other.state == this.state &&
          other.attempts == this.attempts &&
          other.lastError == this.lastError);
}

class SyncQueueEntriesCompanion extends UpdateCompanion<SyncQueueEntry> {
  final Value<String> operationId;
  final Value<String> entityType;
  final Value<String> entityId;
  final Value<String> kind;
  final Value<int?> baseVersion;
  final Value<DateTime> occurredAt;
  final Value<String> payloadJson;
  final Value<String> state;
  final Value<int> attempts;
  final Value<String?> lastError;
  final Value<int> rowid;
  const SyncQueueEntriesCompanion({
    this.operationId = const Value.absent(),
    this.entityType = const Value.absent(),
    this.entityId = const Value.absent(),
    this.kind = const Value.absent(),
    this.baseVersion = const Value.absent(),
    this.occurredAt = const Value.absent(),
    this.payloadJson = const Value.absent(),
    this.state = const Value.absent(),
    this.attempts = const Value.absent(),
    this.lastError = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  SyncQueueEntriesCompanion.insert({
    required String operationId,
    required String entityType,
    required String entityId,
    required String kind,
    this.baseVersion = const Value.absent(),
    required DateTime occurredAt,
    required String payloadJson,
    this.state = const Value.absent(),
    this.attempts = const Value.absent(),
    this.lastError = const Value.absent(),
    this.rowid = const Value.absent(),
  })  : operationId = Value(operationId),
        entityType = Value(entityType),
        entityId = Value(entityId),
        kind = Value(kind),
        occurredAt = Value(occurredAt),
        payloadJson = Value(payloadJson);
  static Insertable<SyncQueueEntry> custom({
    Expression<String>? operationId,
    Expression<String>? entityType,
    Expression<String>? entityId,
    Expression<String>? kind,
    Expression<int>? baseVersion,
    Expression<DateTime>? occurredAt,
    Expression<String>? payloadJson,
    Expression<String>? state,
    Expression<int>? attempts,
    Expression<String>? lastError,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (operationId != null) 'operation_id': operationId,
      if (entityType != null) 'entity_type': entityType,
      if (entityId != null) 'entity_id': entityId,
      if (kind != null) 'kind': kind,
      if (baseVersion != null) 'base_version': baseVersion,
      if (occurredAt != null) 'occurred_at': occurredAt,
      if (payloadJson != null) 'payload_json': payloadJson,
      if (state != null) 'state': state,
      if (attempts != null) 'attempts': attempts,
      if (lastError != null) 'last_error': lastError,
      if (rowid != null) 'rowid': rowid,
    });
  }

  SyncQueueEntriesCompanion copyWith(
      {Value<String>? operationId,
      Value<String>? entityType,
      Value<String>? entityId,
      Value<String>? kind,
      Value<int?>? baseVersion,
      Value<DateTime>? occurredAt,
      Value<String>? payloadJson,
      Value<String>? state,
      Value<int>? attempts,
      Value<String?>? lastError,
      Value<int>? rowid}) {
    return SyncQueueEntriesCompanion(
      operationId: operationId ?? this.operationId,
      entityType: entityType ?? this.entityType,
      entityId: entityId ?? this.entityId,
      kind: kind ?? this.kind,
      baseVersion: baseVersion ?? this.baseVersion,
      occurredAt: occurredAt ?? this.occurredAt,
      payloadJson: payloadJson ?? this.payloadJson,
      state: state ?? this.state,
      attempts: attempts ?? this.attempts,
      lastError: lastError ?? this.lastError,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (operationId.present) {
      map['operation_id'] = Variable<String>(operationId.value);
    }
    if (entityType.present) {
      map['entity_type'] = Variable<String>(entityType.value);
    }
    if (entityId.present) {
      map['entity_id'] = Variable<String>(entityId.value);
    }
    if (kind.present) {
      map['kind'] = Variable<String>(kind.value);
    }
    if (baseVersion.present) {
      map['base_version'] = Variable<int>(baseVersion.value);
    }
    if (occurredAt.present) {
      map['occurred_at'] = Variable<DateTime>(occurredAt.value);
    }
    if (payloadJson.present) {
      map['payload_json'] = Variable<String>(payloadJson.value);
    }
    if (state.present) {
      map['state'] = Variable<String>(state.value);
    }
    if (attempts.present) {
      map['attempts'] = Variable<int>(attempts.value);
    }
    if (lastError.present) {
      map['last_error'] = Variable<String>(lastError.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('SyncQueueEntriesCompanion(')
          ..write('operationId: $operationId, ')
          ..write('entityType: $entityType, ')
          ..write('entityId: $entityId, ')
          ..write('kind: $kind, ')
          ..write('baseVersion: $baseVersion, ')
          ..write('occurredAt: $occurredAt, ')
          ..write('payloadJson: $payloadJson, ')
          ..write('state: $state, ')
          ..write('attempts: $attempts, ')
          ..write('lastError: $lastError, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $WorkOrderTransitionEntriesTable extends WorkOrderTransitionEntries
    with TableInfo<$WorkOrderTransitionEntriesTable, WorkOrderTransitionEntry> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $WorkOrderTransitionEntriesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _operationIdMeta =
      const VerificationMeta('operationId');
  @override
  late final GeneratedColumn<String> operationId = GeneratedColumn<String>(
      'operation_id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _workOrderIdMeta =
      const VerificationMeta('workOrderId');
  @override
  late final GeneratedColumn<String> workOrderId = GeneratedColumn<String>(
      'work_order_id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _fromStatusMeta =
      const VerificationMeta('fromStatus');
  @override
  late final GeneratedColumn<String> fromStatus = GeneratedColumn<String>(
      'from_status', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _toStatusMeta =
      const VerificationMeta('toStatus');
  @override
  late final GeneratedColumn<String> toStatus = GeneratedColumn<String>(
      'to_status', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _noteMeta = const VerificationMeta('note');
  @override
  late final GeneratedColumn<String> note = GeneratedColumn<String>(
      'note', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _latitudeMeta =
      const VerificationMeta('latitude');
  @override
  late final GeneratedColumn<double> latitude = GeneratedColumn<double>(
      'latitude', aliasedName, true,
      type: DriftSqlType.double, requiredDuringInsert: false);
  static const VerificationMeta _longitudeMeta =
      const VerificationMeta('longitude');
  @override
  late final GeneratedColumn<double> longitude = GeneratedColumn<double>(
      'longitude', aliasedName, true,
      type: DriftSqlType.double, requiredDuringInsert: false);
  static const VerificationMeta _occurredAtMeta =
      const VerificationMeta('occurredAt');
  @override
  late final GeneratedColumn<DateTime> occurredAt = GeneratedColumn<DateTime>(
      'occurred_at', aliasedName, false,
      type: DriftSqlType.dateTime, requiredDuringInsert: true);
  @override
  List<GeneratedColumn> get $columns => [
        operationId,
        workOrderId,
        fromStatus,
        toStatus,
        note,
        latitude,
        longitude,
        occurredAt
      ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'work_order_transition_entries';
  @override
  VerificationContext validateIntegrity(
      Insertable<WorkOrderTransitionEntry> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('operation_id')) {
      context.handle(
          _operationIdMeta,
          operationId.isAcceptableOrUnknown(
              data['operation_id']!, _operationIdMeta));
    } else if (isInserting) {
      context.missing(_operationIdMeta);
    }
    if (data.containsKey('work_order_id')) {
      context.handle(
          _workOrderIdMeta,
          workOrderId.isAcceptableOrUnknown(
              data['work_order_id']!, _workOrderIdMeta));
    } else if (isInserting) {
      context.missing(_workOrderIdMeta);
    }
    if (data.containsKey('from_status')) {
      context.handle(
          _fromStatusMeta,
          fromStatus.isAcceptableOrUnknown(
              data['from_status']!, _fromStatusMeta));
    } else if (isInserting) {
      context.missing(_fromStatusMeta);
    }
    if (data.containsKey('to_status')) {
      context.handle(_toStatusMeta,
          toStatus.isAcceptableOrUnknown(data['to_status']!, _toStatusMeta));
    } else if (isInserting) {
      context.missing(_toStatusMeta);
    }
    if (data.containsKey('note')) {
      context.handle(
          _noteMeta, note.isAcceptableOrUnknown(data['note']!, _noteMeta));
    }
    if (data.containsKey('latitude')) {
      context.handle(_latitudeMeta,
          latitude.isAcceptableOrUnknown(data['latitude']!, _latitudeMeta));
    }
    if (data.containsKey('longitude')) {
      context.handle(_longitudeMeta,
          longitude.isAcceptableOrUnknown(data['longitude']!, _longitudeMeta));
    }
    if (data.containsKey('occurred_at')) {
      context.handle(
          _occurredAtMeta,
          occurredAt.isAcceptableOrUnknown(
              data['occurred_at']!, _occurredAtMeta));
    } else if (isInserting) {
      context.missing(_occurredAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {operationId};
  @override
  WorkOrderTransitionEntry map(Map<String, dynamic> data,
      {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return WorkOrderTransitionEntry(
      operationId: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}operation_id'])!,
      workOrderId: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}work_order_id'])!,
      fromStatus: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}from_status'])!,
      toStatus: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}to_status'])!,
      note: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}note']),
      latitude: attachedDatabase.typeMapping
          .read(DriftSqlType.double, data['${effectivePrefix}latitude']),
      longitude: attachedDatabase.typeMapping
          .read(DriftSqlType.double, data['${effectivePrefix}longitude']),
      occurredAt: attachedDatabase.typeMapping
          .read(DriftSqlType.dateTime, data['${effectivePrefix}occurred_at'])!,
    );
  }

  @override
  $WorkOrderTransitionEntriesTable createAlias(String alias) {
    return $WorkOrderTransitionEntriesTable(attachedDatabase, alias);
  }
}

class WorkOrderTransitionEntry extends DataClass
    implements Insertable<WorkOrderTransitionEntry> {
  final String operationId;
  final String workOrderId;
  final String fromStatus;
  final String toStatus;
  final String? note;
  final double? latitude;
  final double? longitude;
  final DateTime occurredAt;
  const WorkOrderTransitionEntry(
      {required this.operationId,
      required this.workOrderId,
      required this.fromStatus,
      required this.toStatus,
      this.note,
      this.latitude,
      this.longitude,
      required this.occurredAt});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['operation_id'] = Variable<String>(operationId);
    map['work_order_id'] = Variable<String>(workOrderId);
    map['from_status'] = Variable<String>(fromStatus);
    map['to_status'] = Variable<String>(toStatus);
    if (!nullToAbsent || note != null) {
      map['note'] = Variable<String>(note);
    }
    if (!nullToAbsent || latitude != null) {
      map['latitude'] = Variable<double>(latitude);
    }
    if (!nullToAbsent || longitude != null) {
      map['longitude'] = Variable<double>(longitude);
    }
    map['occurred_at'] = Variable<DateTime>(occurredAt);
    return map;
  }

  WorkOrderTransitionEntriesCompanion toCompanion(bool nullToAbsent) {
    return WorkOrderTransitionEntriesCompanion(
      operationId: Value(operationId),
      workOrderId: Value(workOrderId),
      fromStatus: Value(fromStatus),
      toStatus: Value(toStatus),
      note: note == null && nullToAbsent ? const Value.absent() : Value(note),
      latitude: latitude == null && nullToAbsent
          ? const Value.absent()
          : Value(latitude),
      longitude: longitude == null && nullToAbsent
          ? const Value.absent()
          : Value(longitude),
      occurredAt: Value(occurredAt),
    );
  }

  factory WorkOrderTransitionEntry.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return WorkOrderTransitionEntry(
      operationId: serializer.fromJson<String>(json['operationId']),
      workOrderId: serializer.fromJson<String>(json['workOrderId']),
      fromStatus: serializer.fromJson<String>(json['fromStatus']),
      toStatus: serializer.fromJson<String>(json['toStatus']),
      note: serializer.fromJson<String?>(json['note']),
      latitude: serializer.fromJson<double?>(json['latitude']),
      longitude: serializer.fromJson<double?>(json['longitude']),
      occurredAt: serializer.fromJson<DateTime>(json['occurredAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'operationId': serializer.toJson<String>(operationId),
      'workOrderId': serializer.toJson<String>(workOrderId),
      'fromStatus': serializer.toJson<String>(fromStatus),
      'toStatus': serializer.toJson<String>(toStatus),
      'note': serializer.toJson<String?>(note),
      'latitude': serializer.toJson<double?>(latitude),
      'longitude': serializer.toJson<double?>(longitude),
      'occurredAt': serializer.toJson<DateTime>(occurredAt),
    };
  }

  WorkOrderTransitionEntry copyWith(
          {String? operationId,
          String? workOrderId,
          String? fromStatus,
          String? toStatus,
          Value<String?> note = const Value.absent(),
          Value<double?> latitude = const Value.absent(),
          Value<double?> longitude = const Value.absent(),
          DateTime? occurredAt}) =>
      WorkOrderTransitionEntry(
        operationId: operationId ?? this.operationId,
        workOrderId: workOrderId ?? this.workOrderId,
        fromStatus: fromStatus ?? this.fromStatus,
        toStatus: toStatus ?? this.toStatus,
        note: note.present ? note.value : this.note,
        latitude: latitude.present ? latitude.value : this.latitude,
        longitude: longitude.present ? longitude.value : this.longitude,
        occurredAt: occurredAt ?? this.occurredAt,
      );
  WorkOrderTransitionEntry copyWithCompanion(
      WorkOrderTransitionEntriesCompanion data) {
    return WorkOrderTransitionEntry(
      operationId:
          data.operationId.present ? data.operationId.value : this.operationId,
      workOrderId:
          data.workOrderId.present ? data.workOrderId.value : this.workOrderId,
      fromStatus:
          data.fromStatus.present ? data.fromStatus.value : this.fromStatus,
      toStatus: data.toStatus.present ? data.toStatus.value : this.toStatus,
      note: data.note.present ? data.note.value : this.note,
      latitude: data.latitude.present ? data.latitude.value : this.latitude,
      longitude: data.longitude.present ? data.longitude.value : this.longitude,
      occurredAt:
          data.occurredAt.present ? data.occurredAt.value : this.occurredAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('WorkOrderTransitionEntry(')
          ..write('operationId: $operationId, ')
          ..write('workOrderId: $workOrderId, ')
          ..write('fromStatus: $fromStatus, ')
          ..write('toStatus: $toStatus, ')
          ..write('note: $note, ')
          ..write('latitude: $latitude, ')
          ..write('longitude: $longitude, ')
          ..write('occurredAt: $occurredAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(operationId, workOrderId, fromStatus,
      toStatus, note, latitude, longitude, occurredAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is WorkOrderTransitionEntry &&
          other.operationId == this.operationId &&
          other.workOrderId == this.workOrderId &&
          other.fromStatus == this.fromStatus &&
          other.toStatus == this.toStatus &&
          other.note == this.note &&
          other.latitude == this.latitude &&
          other.longitude == this.longitude &&
          other.occurredAt == this.occurredAt);
}

class WorkOrderTransitionEntriesCompanion
    extends UpdateCompanion<WorkOrderTransitionEntry> {
  final Value<String> operationId;
  final Value<String> workOrderId;
  final Value<String> fromStatus;
  final Value<String> toStatus;
  final Value<String?> note;
  final Value<double?> latitude;
  final Value<double?> longitude;
  final Value<DateTime> occurredAt;
  final Value<int> rowid;
  const WorkOrderTransitionEntriesCompanion({
    this.operationId = const Value.absent(),
    this.workOrderId = const Value.absent(),
    this.fromStatus = const Value.absent(),
    this.toStatus = const Value.absent(),
    this.note = const Value.absent(),
    this.latitude = const Value.absent(),
    this.longitude = const Value.absent(),
    this.occurredAt = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  WorkOrderTransitionEntriesCompanion.insert({
    required String operationId,
    required String workOrderId,
    required String fromStatus,
    required String toStatus,
    this.note = const Value.absent(),
    this.latitude = const Value.absent(),
    this.longitude = const Value.absent(),
    required DateTime occurredAt,
    this.rowid = const Value.absent(),
  })  : operationId = Value(operationId),
        workOrderId = Value(workOrderId),
        fromStatus = Value(fromStatus),
        toStatus = Value(toStatus),
        occurredAt = Value(occurredAt);
  static Insertable<WorkOrderTransitionEntry> custom({
    Expression<String>? operationId,
    Expression<String>? workOrderId,
    Expression<String>? fromStatus,
    Expression<String>? toStatus,
    Expression<String>? note,
    Expression<double>? latitude,
    Expression<double>? longitude,
    Expression<DateTime>? occurredAt,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (operationId != null) 'operation_id': operationId,
      if (workOrderId != null) 'work_order_id': workOrderId,
      if (fromStatus != null) 'from_status': fromStatus,
      if (toStatus != null) 'to_status': toStatus,
      if (note != null) 'note': note,
      if (latitude != null) 'latitude': latitude,
      if (longitude != null) 'longitude': longitude,
      if (occurredAt != null) 'occurred_at': occurredAt,
      if (rowid != null) 'rowid': rowid,
    });
  }

  WorkOrderTransitionEntriesCompanion copyWith(
      {Value<String>? operationId,
      Value<String>? workOrderId,
      Value<String>? fromStatus,
      Value<String>? toStatus,
      Value<String?>? note,
      Value<double?>? latitude,
      Value<double?>? longitude,
      Value<DateTime>? occurredAt,
      Value<int>? rowid}) {
    return WorkOrderTransitionEntriesCompanion(
      operationId: operationId ?? this.operationId,
      workOrderId: workOrderId ?? this.workOrderId,
      fromStatus: fromStatus ?? this.fromStatus,
      toStatus: toStatus ?? this.toStatus,
      note: note ?? this.note,
      latitude: latitude ?? this.latitude,
      longitude: longitude ?? this.longitude,
      occurredAt: occurredAt ?? this.occurredAt,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (operationId.present) {
      map['operation_id'] = Variable<String>(operationId.value);
    }
    if (workOrderId.present) {
      map['work_order_id'] = Variable<String>(workOrderId.value);
    }
    if (fromStatus.present) {
      map['from_status'] = Variable<String>(fromStatus.value);
    }
    if (toStatus.present) {
      map['to_status'] = Variable<String>(toStatus.value);
    }
    if (note.present) {
      map['note'] = Variable<String>(note.value);
    }
    if (latitude.present) {
      map['latitude'] = Variable<double>(latitude.value);
    }
    if (longitude.present) {
      map['longitude'] = Variable<double>(longitude.value);
    }
    if (occurredAt.present) {
      map['occurred_at'] = Variable<DateTime>(occurredAt.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('WorkOrderTransitionEntriesCompanion(')
          ..write('operationId: $operationId, ')
          ..write('workOrderId: $workOrderId, ')
          ..write('fromStatus: $fromStatus, ')
          ..write('toStatus: $toStatus, ')
          ..write('note: $note, ')
          ..write('latitude: $latitude, ')
          ..write('longitude: $longitude, ')
          ..write('occurredAt: $occurredAt, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $EvidenceEntriesTable extends EvidenceEntries
    with TableInfo<$EvidenceEntriesTable, EvidenceEntry> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $EvidenceEntriesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
      'id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _workOrderIdMeta =
      const VerificationMeta('workOrderId');
  @override
  late final GeneratedColumn<String> workOrderId = GeneratedColumn<String>(
      'work_order_id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _categoryMeta =
      const VerificationMeta('category');
  @override
  late final GeneratedColumn<String> category = GeneratedColumn<String>(
      'category', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _localPathMeta =
      const VerificationMeta('localPath');
  @override
  late final GeneratedColumn<String> localPath = GeneratedColumn<String>(
      'local_path', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _sha256Meta = const VerificationMeta('sha256');
  @override
  late final GeneratedColumn<String> sha256 = GeneratedColumn<String>(
      'sha256', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _stateMeta = const VerificationMeta('state');
  @override
  late final GeneratedColumn<String> state = GeneratedColumn<String>(
      'state', aliasedName, false,
      type: DriftSqlType.string,
      requiredDuringInsert: false,
      defaultValue: const Constant('pending'));
  static const VerificationMeta _createdAtMeta =
      const VerificationMeta('createdAt');
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
      'created_at', aliasedName, false,
      type: DriftSqlType.dateTime, requiredDuringInsert: true);
  @override
  List<GeneratedColumn> get $columns =>
      [id, workOrderId, category, localPath, sha256, state, createdAt];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'evidence_entries';
  @override
  VerificationContext validateIntegrity(Insertable<EvidenceEntry> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('work_order_id')) {
      context.handle(
          _workOrderIdMeta,
          workOrderId.isAcceptableOrUnknown(
              data['work_order_id']!, _workOrderIdMeta));
    } else if (isInserting) {
      context.missing(_workOrderIdMeta);
    }
    if (data.containsKey('category')) {
      context.handle(_categoryMeta,
          category.isAcceptableOrUnknown(data['category']!, _categoryMeta));
    } else if (isInserting) {
      context.missing(_categoryMeta);
    }
    if (data.containsKey('local_path')) {
      context.handle(_localPathMeta,
          localPath.isAcceptableOrUnknown(data['local_path']!, _localPathMeta));
    } else if (isInserting) {
      context.missing(_localPathMeta);
    }
    if (data.containsKey('sha256')) {
      context.handle(_sha256Meta,
          sha256.isAcceptableOrUnknown(data['sha256']!, _sha256Meta));
    } else if (isInserting) {
      context.missing(_sha256Meta);
    }
    if (data.containsKey('state')) {
      context.handle(
          _stateMeta, state.isAcceptableOrUnknown(data['state']!, _stateMeta));
    }
    if (data.containsKey('created_at')) {
      context.handle(_createdAtMeta,
          createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta));
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  EvidenceEntry map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return EvidenceEntry(
      id: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      workOrderId: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}work_order_id'])!,
      category: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}category'])!,
      localPath: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}local_path'])!,
      sha256: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}sha256'])!,
      state: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}state'])!,
      createdAt: attachedDatabase.typeMapping
          .read(DriftSqlType.dateTime, data['${effectivePrefix}created_at'])!,
    );
  }

  @override
  $EvidenceEntriesTable createAlias(String alias) {
    return $EvidenceEntriesTable(attachedDatabase, alias);
  }
}

class EvidenceEntry extends DataClass implements Insertable<EvidenceEntry> {
  final String id;
  final String workOrderId;
  final String category;
  final String localPath;
  final String sha256;
  final String state;
  final DateTime createdAt;
  const EvidenceEntry(
      {required this.id,
      required this.workOrderId,
      required this.category,
      required this.localPath,
      required this.sha256,
      required this.state,
      required this.createdAt});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['work_order_id'] = Variable<String>(workOrderId);
    map['category'] = Variable<String>(category);
    map['local_path'] = Variable<String>(localPath);
    map['sha256'] = Variable<String>(sha256);
    map['state'] = Variable<String>(state);
    map['created_at'] = Variable<DateTime>(createdAt);
    return map;
  }

  EvidenceEntriesCompanion toCompanion(bool nullToAbsent) {
    return EvidenceEntriesCompanion(
      id: Value(id),
      workOrderId: Value(workOrderId),
      category: Value(category),
      localPath: Value(localPath),
      sha256: Value(sha256),
      state: Value(state),
      createdAt: Value(createdAt),
    );
  }

  factory EvidenceEntry.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return EvidenceEntry(
      id: serializer.fromJson<String>(json['id']),
      workOrderId: serializer.fromJson<String>(json['workOrderId']),
      category: serializer.fromJson<String>(json['category']),
      localPath: serializer.fromJson<String>(json['localPath']),
      sha256: serializer.fromJson<String>(json['sha256']),
      state: serializer.fromJson<String>(json['state']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'workOrderId': serializer.toJson<String>(workOrderId),
      'category': serializer.toJson<String>(category),
      'localPath': serializer.toJson<String>(localPath),
      'sha256': serializer.toJson<String>(sha256),
      'state': serializer.toJson<String>(state),
      'createdAt': serializer.toJson<DateTime>(createdAt),
    };
  }

  EvidenceEntry copyWith(
          {String? id,
          String? workOrderId,
          String? category,
          String? localPath,
          String? sha256,
          String? state,
          DateTime? createdAt}) =>
      EvidenceEntry(
        id: id ?? this.id,
        workOrderId: workOrderId ?? this.workOrderId,
        category: category ?? this.category,
        localPath: localPath ?? this.localPath,
        sha256: sha256 ?? this.sha256,
        state: state ?? this.state,
        createdAt: createdAt ?? this.createdAt,
      );
  EvidenceEntry copyWithCompanion(EvidenceEntriesCompanion data) {
    return EvidenceEntry(
      id: data.id.present ? data.id.value : this.id,
      workOrderId:
          data.workOrderId.present ? data.workOrderId.value : this.workOrderId,
      category: data.category.present ? data.category.value : this.category,
      localPath: data.localPath.present ? data.localPath.value : this.localPath,
      sha256: data.sha256.present ? data.sha256.value : this.sha256,
      state: data.state.present ? data.state.value : this.state,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('EvidenceEntry(')
          ..write('id: $id, ')
          ..write('workOrderId: $workOrderId, ')
          ..write('category: $category, ')
          ..write('localPath: $localPath, ')
          ..write('sha256: $sha256, ')
          ..write('state: $state, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
      id, workOrderId, category, localPath, sha256, state, createdAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is EvidenceEntry &&
          other.id == this.id &&
          other.workOrderId == this.workOrderId &&
          other.category == this.category &&
          other.localPath == this.localPath &&
          other.sha256 == this.sha256 &&
          other.state == this.state &&
          other.createdAt == this.createdAt);
}

class EvidenceEntriesCompanion extends UpdateCompanion<EvidenceEntry> {
  final Value<String> id;
  final Value<String> workOrderId;
  final Value<String> category;
  final Value<String> localPath;
  final Value<String> sha256;
  final Value<String> state;
  final Value<DateTime> createdAt;
  final Value<int> rowid;
  const EvidenceEntriesCompanion({
    this.id = const Value.absent(),
    this.workOrderId = const Value.absent(),
    this.category = const Value.absent(),
    this.localPath = const Value.absent(),
    this.sha256 = const Value.absent(),
    this.state = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  EvidenceEntriesCompanion.insert({
    required String id,
    required String workOrderId,
    required String category,
    required String localPath,
    required String sha256,
    this.state = const Value.absent(),
    required DateTime createdAt,
    this.rowid = const Value.absent(),
  })  : id = Value(id),
        workOrderId = Value(workOrderId),
        category = Value(category),
        localPath = Value(localPath),
        sha256 = Value(sha256),
        createdAt = Value(createdAt);
  static Insertable<EvidenceEntry> custom({
    Expression<String>? id,
    Expression<String>? workOrderId,
    Expression<String>? category,
    Expression<String>? localPath,
    Expression<String>? sha256,
    Expression<String>? state,
    Expression<DateTime>? createdAt,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (workOrderId != null) 'work_order_id': workOrderId,
      if (category != null) 'category': category,
      if (localPath != null) 'local_path': localPath,
      if (sha256 != null) 'sha256': sha256,
      if (state != null) 'state': state,
      if (createdAt != null) 'created_at': createdAt,
      if (rowid != null) 'rowid': rowid,
    });
  }

  EvidenceEntriesCompanion copyWith(
      {Value<String>? id,
      Value<String>? workOrderId,
      Value<String>? category,
      Value<String>? localPath,
      Value<String>? sha256,
      Value<String>? state,
      Value<DateTime>? createdAt,
      Value<int>? rowid}) {
    return EvidenceEntriesCompanion(
      id: id ?? this.id,
      workOrderId: workOrderId ?? this.workOrderId,
      category: category ?? this.category,
      localPath: localPath ?? this.localPath,
      sha256: sha256 ?? this.sha256,
      state: state ?? this.state,
      createdAt: createdAt ?? this.createdAt,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (workOrderId.present) {
      map['work_order_id'] = Variable<String>(workOrderId.value);
    }
    if (category.present) {
      map['category'] = Variable<String>(category.value);
    }
    if (localPath.present) {
      map['local_path'] = Variable<String>(localPath.value);
    }
    if (sha256.present) {
      map['sha256'] = Variable<String>(sha256.value);
    }
    if (state.present) {
      map['state'] = Variable<String>(state.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('EvidenceEntriesCompanion(')
          ..write('id: $id, ')
          ..write('workOrderId: $workOrderId, ')
          ..write('category: $category, ')
          ..write('localPath: $localPath, ')
          ..write('sha256: $sha256, ')
          ..write('state: $state, ')
          ..write('createdAt: $createdAt, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $EquipmentScanEntriesTable extends EquipmentScanEntries
    with TableInfo<$EquipmentScanEntriesTable, EquipmentScanEntry> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $EquipmentScanEntriesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
      'id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _workOrderIdMeta =
      const VerificationMeta('workOrderId');
  @override
  late final GeneratedColumn<String> workOrderId = GeneratedColumn<String>(
      'work_order_id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _serialMeta = const VerificationMeta('serial');
  @override
  late final GeneratedColumn<String> serial = GeneratedColumn<String>(
      'serial', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _stateMeta = const VerificationMeta('state');
  @override
  late final GeneratedColumn<String> state = GeneratedColumn<String>(
      'state', aliasedName, false,
      type: DriftSqlType.string,
      requiredDuringInsert: false,
      defaultValue: const Constant('pending'));
  static const VerificationMeta _createdAtMeta =
      const VerificationMeta('createdAt');
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
      'created_at', aliasedName, false,
      type: DriftSqlType.dateTime, requiredDuringInsert: true);
  @override
  List<GeneratedColumn> get $columns =>
      [id, workOrderId, serial, state, createdAt];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'equipment_scan_entries';
  @override
  VerificationContext validateIntegrity(Insertable<EquipmentScanEntry> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('work_order_id')) {
      context.handle(
          _workOrderIdMeta,
          workOrderId.isAcceptableOrUnknown(
              data['work_order_id']!, _workOrderIdMeta));
    } else if (isInserting) {
      context.missing(_workOrderIdMeta);
    }
    if (data.containsKey('serial')) {
      context.handle(_serialMeta,
          serial.isAcceptableOrUnknown(data['serial']!, _serialMeta));
    } else if (isInserting) {
      context.missing(_serialMeta);
    }
    if (data.containsKey('state')) {
      context.handle(
          _stateMeta, state.isAcceptableOrUnknown(data['state']!, _stateMeta));
    }
    if (data.containsKey('created_at')) {
      context.handle(_createdAtMeta,
          createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta));
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  EquipmentScanEntry map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return EquipmentScanEntry(
      id: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      workOrderId: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}work_order_id'])!,
      serial: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}serial'])!,
      state: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}state'])!,
      createdAt: attachedDatabase.typeMapping
          .read(DriftSqlType.dateTime, data['${effectivePrefix}created_at'])!,
    );
  }

  @override
  $EquipmentScanEntriesTable createAlias(String alias) {
    return $EquipmentScanEntriesTable(attachedDatabase, alias);
  }
}

class EquipmentScanEntry extends DataClass
    implements Insertable<EquipmentScanEntry> {
  final String id;
  final String workOrderId;
  final String serial;
  final String state;
  final DateTime createdAt;
  const EquipmentScanEntry(
      {required this.id,
      required this.workOrderId,
      required this.serial,
      required this.state,
      required this.createdAt});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['work_order_id'] = Variable<String>(workOrderId);
    map['serial'] = Variable<String>(serial);
    map['state'] = Variable<String>(state);
    map['created_at'] = Variable<DateTime>(createdAt);
    return map;
  }

  EquipmentScanEntriesCompanion toCompanion(bool nullToAbsent) {
    return EquipmentScanEntriesCompanion(
      id: Value(id),
      workOrderId: Value(workOrderId),
      serial: Value(serial),
      state: Value(state),
      createdAt: Value(createdAt),
    );
  }

  factory EquipmentScanEntry.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return EquipmentScanEntry(
      id: serializer.fromJson<String>(json['id']),
      workOrderId: serializer.fromJson<String>(json['workOrderId']),
      serial: serializer.fromJson<String>(json['serial']),
      state: serializer.fromJson<String>(json['state']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'workOrderId': serializer.toJson<String>(workOrderId),
      'serial': serializer.toJson<String>(serial),
      'state': serializer.toJson<String>(state),
      'createdAt': serializer.toJson<DateTime>(createdAt),
    };
  }

  EquipmentScanEntry copyWith(
          {String? id,
          String? workOrderId,
          String? serial,
          String? state,
          DateTime? createdAt}) =>
      EquipmentScanEntry(
        id: id ?? this.id,
        workOrderId: workOrderId ?? this.workOrderId,
        serial: serial ?? this.serial,
        state: state ?? this.state,
        createdAt: createdAt ?? this.createdAt,
      );
  EquipmentScanEntry copyWithCompanion(EquipmentScanEntriesCompanion data) {
    return EquipmentScanEntry(
      id: data.id.present ? data.id.value : this.id,
      workOrderId:
          data.workOrderId.present ? data.workOrderId.value : this.workOrderId,
      serial: data.serial.present ? data.serial.value : this.serial,
      state: data.state.present ? data.state.value : this.state,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('EquipmentScanEntry(')
          ..write('id: $id, ')
          ..write('workOrderId: $workOrderId, ')
          ..write('serial: $serial, ')
          ..write('state: $state, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(id, workOrderId, serial, state, createdAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is EquipmentScanEntry &&
          other.id == this.id &&
          other.workOrderId == this.workOrderId &&
          other.serial == this.serial &&
          other.state == this.state &&
          other.createdAt == this.createdAt);
}

class EquipmentScanEntriesCompanion
    extends UpdateCompanion<EquipmentScanEntry> {
  final Value<String> id;
  final Value<String> workOrderId;
  final Value<String> serial;
  final Value<String> state;
  final Value<DateTime> createdAt;
  final Value<int> rowid;
  const EquipmentScanEntriesCompanion({
    this.id = const Value.absent(),
    this.workOrderId = const Value.absent(),
    this.serial = const Value.absent(),
    this.state = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  EquipmentScanEntriesCompanion.insert({
    required String id,
    required String workOrderId,
    required String serial,
    this.state = const Value.absent(),
    required DateTime createdAt,
    this.rowid = const Value.absent(),
  })  : id = Value(id),
        workOrderId = Value(workOrderId),
        serial = Value(serial),
        createdAt = Value(createdAt);
  static Insertable<EquipmentScanEntry> custom({
    Expression<String>? id,
    Expression<String>? workOrderId,
    Expression<String>? serial,
    Expression<String>? state,
    Expression<DateTime>? createdAt,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (workOrderId != null) 'work_order_id': workOrderId,
      if (serial != null) 'serial': serial,
      if (state != null) 'state': state,
      if (createdAt != null) 'created_at': createdAt,
      if (rowid != null) 'rowid': rowid,
    });
  }

  EquipmentScanEntriesCompanion copyWith(
      {Value<String>? id,
      Value<String>? workOrderId,
      Value<String>? serial,
      Value<String>? state,
      Value<DateTime>? createdAt,
      Value<int>? rowid}) {
    return EquipmentScanEntriesCompanion(
      id: id ?? this.id,
      workOrderId: workOrderId ?? this.workOrderId,
      serial: serial ?? this.serial,
      state: state ?? this.state,
      createdAt: createdAt ?? this.createdAt,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (workOrderId.present) {
      map['work_order_id'] = Variable<String>(workOrderId.value);
    }
    if (serial.present) {
      map['serial'] = Variable<String>(serial.value);
    }
    if (state.present) {
      map['state'] = Variable<String>(state.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('EquipmentScanEntriesCompanion(')
          ..write('id: $id, ')
          ..write('workOrderId: $workOrderId, ')
          ..write('serial: $serial, ')
          ..write('state: $state, ')
          ..write('createdAt: $createdAt, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $InventoryItemEntriesTable extends InventoryItemEntries
    with TableInfo<$InventoryItemEntriesTable, InventoryItemEntry> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $InventoryItemEntriesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
      'id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _skuMeta = const VerificationMeta('sku');
  @override
  late final GeneratedColumn<String> sku = GeneratedColumn<String>(
      'sku', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _descriptionMeta =
      const VerificationMeta('description');
  @override
  late final GeneratedColumn<String> description = GeneratedColumn<String>(
      'description', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _quantityMeta =
      const VerificationMeta('quantity');
  @override
  late final GeneratedColumn<double> quantity = GeneratedColumn<double>(
      'quantity', aliasedName, false,
      type: DriftSqlType.double, requiredDuringInsert: true);
  static const VerificationMeta _unitMeta = const VerificationMeta('unit');
  @override
  late final GeneratedColumn<String> unit = GeneratedColumn<String>(
      'unit', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _serialNumberMeta =
      const VerificationMeta('serialNumber');
  @override
  late final GeneratedColumn<String> serialNumber = GeneratedColumn<String>(
      'serial_number', aliasedName, true,
      type: DriftSqlType.string, requiredDuringInsert: false);
  static const VerificationMeta _versionMeta =
      const VerificationMeta('version');
  @override
  late final GeneratedColumn<int> version = GeneratedColumn<int>(
      'version', aliasedName, false,
      type: DriftSqlType.int, requiredDuringInsert: true);
  @override
  List<GeneratedColumn> get $columns =>
      [id, sku, description, quantity, unit, serialNumber, version];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'inventory_item_entries';
  @override
  VerificationContext validateIntegrity(Insertable<InventoryItemEntry> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('sku')) {
      context.handle(
          _skuMeta, sku.isAcceptableOrUnknown(data['sku']!, _skuMeta));
    } else if (isInserting) {
      context.missing(_skuMeta);
    }
    if (data.containsKey('description')) {
      context.handle(
          _descriptionMeta,
          description.isAcceptableOrUnknown(
              data['description']!, _descriptionMeta));
    } else if (isInserting) {
      context.missing(_descriptionMeta);
    }
    if (data.containsKey('quantity')) {
      context.handle(_quantityMeta,
          quantity.isAcceptableOrUnknown(data['quantity']!, _quantityMeta));
    } else if (isInserting) {
      context.missing(_quantityMeta);
    }
    if (data.containsKey('unit')) {
      context.handle(
          _unitMeta, unit.isAcceptableOrUnknown(data['unit']!, _unitMeta));
    } else if (isInserting) {
      context.missing(_unitMeta);
    }
    if (data.containsKey('serial_number')) {
      context.handle(
          _serialNumberMeta,
          serialNumber.isAcceptableOrUnknown(
              data['serial_number']!, _serialNumberMeta));
    }
    if (data.containsKey('version')) {
      context.handle(_versionMeta,
          version.isAcceptableOrUnknown(data['version']!, _versionMeta));
    } else if (isInserting) {
      context.missing(_versionMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  InventoryItemEntry map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return InventoryItemEntry(
      id: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      sku: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}sku'])!,
      description: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}description'])!,
      quantity: attachedDatabase.typeMapping
          .read(DriftSqlType.double, data['${effectivePrefix}quantity'])!,
      unit: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}unit'])!,
      serialNumber: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}serial_number']),
      version: attachedDatabase.typeMapping
          .read(DriftSqlType.int, data['${effectivePrefix}version'])!,
    );
  }

  @override
  $InventoryItemEntriesTable createAlias(String alias) {
    return $InventoryItemEntriesTable(attachedDatabase, alias);
  }
}

class InventoryItemEntry extends DataClass
    implements Insertable<InventoryItemEntry> {
  final String id;
  final String sku;
  final String description;
  final double quantity;
  final String unit;
  final String? serialNumber;
  final int version;
  const InventoryItemEntry(
      {required this.id,
      required this.sku,
      required this.description,
      required this.quantity,
      required this.unit,
      this.serialNumber,
      required this.version});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['sku'] = Variable<String>(sku);
    map['description'] = Variable<String>(description);
    map['quantity'] = Variable<double>(quantity);
    map['unit'] = Variable<String>(unit);
    if (!nullToAbsent || serialNumber != null) {
      map['serial_number'] = Variable<String>(serialNumber);
    }
    map['version'] = Variable<int>(version);
    return map;
  }

  InventoryItemEntriesCompanion toCompanion(bool nullToAbsent) {
    return InventoryItemEntriesCompanion(
      id: Value(id),
      sku: Value(sku),
      description: Value(description),
      quantity: Value(quantity),
      unit: Value(unit),
      serialNumber: serialNumber == null && nullToAbsent
          ? const Value.absent()
          : Value(serialNumber),
      version: Value(version),
    );
  }

  factory InventoryItemEntry.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return InventoryItemEntry(
      id: serializer.fromJson<String>(json['id']),
      sku: serializer.fromJson<String>(json['sku']),
      description: serializer.fromJson<String>(json['description']),
      quantity: serializer.fromJson<double>(json['quantity']),
      unit: serializer.fromJson<String>(json['unit']),
      serialNumber: serializer.fromJson<String?>(json['serialNumber']),
      version: serializer.fromJson<int>(json['version']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'sku': serializer.toJson<String>(sku),
      'description': serializer.toJson<String>(description),
      'quantity': serializer.toJson<double>(quantity),
      'unit': serializer.toJson<String>(unit),
      'serialNumber': serializer.toJson<String?>(serialNumber),
      'version': serializer.toJson<int>(version),
    };
  }

  InventoryItemEntry copyWith(
          {String? id,
          String? sku,
          String? description,
          double? quantity,
          String? unit,
          Value<String?> serialNumber = const Value.absent(),
          int? version}) =>
      InventoryItemEntry(
        id: id ?? this.id,
        sku: sku ?? this.sku,
        description: description ?? this.description,
        quantity: quantity ?? this.quantity,
        unit: unit ?? this.unit,
        serialNumber:
            serialNumber.present ? serialNumber.value : this.serialNumber,
        version: version ?? this.version,
      );
  InventoryItemEntry copyWithCompanion(InventoryItemEntriesCompanion data) {
    return InventoryItemEntry(
      id: data.id.present ? data.id.value : this.id,
      sku: data.sku.present ? data.sku.value : this.sku,
      description:
          data.description.present ? data.description.value : this.description,
      quantity: data.quantity.present ? data.quantity.value : this.quantity,
      unit: data.unit.present ? data.unit.value : this.unit,
      serialNumber: data.serialNumber.present
          ? data.serialNumber.value
          : this.serialNumber,
      version: data.version.present ? data.version.value : this.version,
    );
  }

  @override
  String toString() {
    return (StringBuffer('InventoryItemEntry(')
          ..write('id: $id, ')
          ..write('sku: $sku, ')
          ..write('description: $description, ')
          ..write('quantity: $quantity, ')
          ..write('unit: $unit, ')
          ..write('serialNumber: $serialNumber, ')
          ..write('version: $version')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode =>
      Object.hash(id, sku, description, quantity, unit, serialNumber, version);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is InventoryItemEntry &&
          other.id == this.id &&
          other.sku == this.sku &&
          other.description == this.description &&
          other.quantity == this.quantity &&
          other.unit == this.unit &&
          other.serialNumber == this.serialNumber &&
          other.version == this.version);
}

class InventoryItemEntriesCompanion
    extends UpdateCompanion<InventoryItemEntry> {
  final Value<String> id;
  final Value<String> sku;
  final Value<String> description;
  final Value<double> quantity;
  final Value<String> unit;
  final Value<String?> serialNumber;
  final Value<int> version;
  final Value<int> rowid;
  const InventoryItemEntriesCompanion({
    this.id = const Value.absent(),
    this.sku = const Value.absent(),
    this.description = const Value.absent(),
    this.quantity = const Value.absent(),
    this.unit = const Value.absent(),
    this.serialNumber = const Value.absent(),
    this.version = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  InventoryItemEntriesCompanion.insert({
    required String id,
    required String sku,
    required String description,
    required double quantity,
    required String unit,
    this.serialNumber = const Value.absent(),
    required int version,
    this.rowid = const Value.absent(),
  })  : id = Value(id),
        sku = Value(sku),
        description = Value(description),
        quantity = Value(quantity),
        unit = Value(unit),
        version = Value(version);
  static Insertable<InventoryItemEntry> custom({
    Expression<String>? id,
    Expression<String>? sku,
    Expression<String>? description,
    Expression<double>? quantity,
    Expression<String>? unit,
    Expression<String>? serialNumber,
    Expression<int>? version,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (sku != null) 'sku': sku,
      if (description != null) 'description': description,
      if (quantity != null) 'quantity': quantity,
      if (unit != null) 'unit': unit,
      if (serialNumber != null) 'serial_number': serialNumber,
      if (version != null) 'version': version,
      if (rowid != null) 'rowid': rowid,
    });
  }

  InventoryItemEntriesCompanion copyWith(
      {Value<String>? id,
      Value<String>? sku,
      Value<String>? description,
      Value<double>? quantity,
      Value<String>? unit,
      Value<String?>? serialNumber,
      Value<int>? version,
      Value<int>? rowid}) {
    return InventoryItemEntriesCompanion(
      id: id ?? this.id,
      sku: sku ?? this.sku,
      description: description ?? this.description,
      quantity: quantity ?? this.quantity,
      unit: unit ?? this.unit,
      serialNumber: serialNumber ?? this.serialNumber,
      version: version ?? this.version,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (sku.present) {
      map['sku'] = Variable<String>(sku.value);
    }
    if (description.present) {
      map['description'] = Variable<String>(description.value);
    }
    if (quantity.present) {
      map['quantity'] = Variable<double>(quantity.value);
    }
    if (unit.present) {
      map['unit'] = Variable<String>(unit.value);
    }
    if (serialNumber.present) {
      map['serial_number'] = Variable<String>(serialNumber.value);
    }
    if (version.present) {
      map['version'] = Variable<int>(version.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('InventoryItemEntriesCompanion(')
          ..write('id: $id, ')
          ..write('sku: $sku, ')
          ..write('description: $description, ')
          ..write('quantity: $quantity, ')
          ..write('unit: $unit, ')
          ..write('serialNumber: $serialNumber, ')
          ..write('version: $version, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $InventoryMovementEntriesTable extends InventoryMovementEntries
    with TableInfo<$InventoryMovementEntriesTable, InventoryMovementEntry> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $InventoryMovementEntriesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
      'id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _workOrderIdMeta =
      const VerificationMeta('workOrderId');
  @override
  late final GeneratedColumn<String> workOrderId = GeneratedColumn<String>(
      'work_order_id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _itemIdMeta = const VerificationMeta('itemId');
  @override
  late final GeneratedColumn<String> itemId = GeneratedColumn<String>(
      'item_id', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _quantityMeta =
      const VerificationMeta('quantity');
  @override
  late final GeneratedColumn<double> quantity = GeneratedColumn<double>(
      'quantity', aliasedName, false,
      type: DriftSqlType.double, requiredDuringInsert: true);
  static const VerificationMeta _kindMeta = const VerificationMeta('kind');
  @override
  late final GeneratedColumn<String> kind = GeneratedColumn<String>(
      'kind', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _occurredAtMeta =
      const VerificationMeta('occurredAt');
  @override
  late final GeneratedColumn<DateTime> occurredAt = GeneratedColumn<DateTime>(
      'occurred_at', aliasedName, false,
      type: DriftSqlType.dateTime, requiredDuringInsert: true);
  @override
  List<GeneratedColumn> get $columns =>
      [id, workOrderId, itemId, quantity, kind, occurredAt];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'inventory_movement_entries';
  @override
  VerificationContext validateIntegrity(
      Insertable<InventoryMovementEntry> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('work_order_id')) {
      context.handle(
          _workOrderIdMeta,
          workOrderId.isAcceptableOrUnknown(
              data['work_order_id']!, _workOrderIdMeta));
    } else if (isInserting) {
      context.missing(_workOrderIdMeta);
    }
    if (data.containsKey('item_id')) {
      context.handle(_itemIdMeta,
          itemId.isAcceptableOrUnknown(data['item_id']!, _itemIdMeta));
    } else if (isInserting) {
      context.missing(_itemIdMeta);
    }
    if (data.containsKey('quantity')) {
      context.handle(_quantityMeta,
          quantity.isAcceptableOrUnknown(data['quantity']!, _quantityMeta));
    } else if (isInserting) {
      context.missing(_quantityMeta);
    }
    if (data.containsKey('kind')) {
      context.handle(
          _kindMeta, kind.isAcceptableOrUnknown(data['kind']!, _kindMeta));
    } else if (isInserting) {
      context.missing(_kindMeta);
    }
    if (data.containsKey('occurred_at')) {
      context.handle(
          _occurredAtMeta,
          occurredAt.isAcceptableOrUnknown(
              data['occurred_at']!, _occurredAtMeta));
    } else if (isInserting) {
      context.missing(_occurredAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  InventoryMovementEntry map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return InventoryMovementEntry(
      id: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}id'])!,
      workOrderId: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}work_order_id'])!,
      itemId: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}item_id'])!,
      quantity: attachedDatabase.typeMapping
          .read(DriftSqlType.double, data['${effectivePrefix}quantity'])!,
      kind: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}kind'])!,
      occurredAt: attachedDatabase.typeMapping
          .read(DriftSqlType.dateTime, data['${effectivePrefix}occurred_at'])!,
    );
  }

  @override
  $InventoryMovementEntriesTable createAlias(String alias) {
    return $InventoryMovementEntriesTable(attachedDatabase, alias);
  }
}

class InventoryMovementEntry extends DataClass
    implements Insertable<InventoryMovementEntry> {
  final String id;
  final String workOrderId;
  final String itemId;
  final double quantity;
  final String kind;
  final DateTime occurredAt;
  const InventoryMovementEntry(
      {required this.id,
      required this.workOrderId,
      required this.itemId,
      required this.quantity,
      required this.kind,
      required this.occurredAt});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['work_order_id'] = Variable<String>(workOrderId);
    map['item_id'] = Variable<String>(itemId);
    map['quantity'] = Variable<double>(quantity);
    map['kind'] = Variable<String>(kind);
    map['occurred_at'] = Variable<DateTime>(occurredAt);
    return map;
  }

  InventoryMovementEntriesCompanion toCompanion(bool nullToAbsent) {
    return InventoryMovementEntriesCompanion(
      id: Value(id),
      workOrderId: Value(workOrderId),
      itemId: Value(itemId),
      quantity: Value(quantity),
      kind: Value(kind),
      occurredAt: Value(occurredAt),
    );
  }

  factory InventoryMovementEntry.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return InventoryMovementEntry(
      id: serializer.fromJson<String>(json['id']),
      workOrderId: serializer.fromJson<String>(json['workOrderId']),
      itemId: serializer.fromJson<String>(json['itemId']),
      quantity: serializer.fromJson<double>(json['quantity']),
      kind: serializer.fromJson<String>(json['kind']),
      occurredAt: serializer.fromJson<DateTime>(json['occurredAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'workOrderId': serializer.toJson<String>(workOrderId),
      'itemId': serializer.toJson<String>(itemId),
      'quantity': serializer.toJson<double>(quantity),
      'kind': serializer.toJson<String>(kind),
      'occurredAt': serializer.toJson<DateTime>(occurredAt),
    };
  }

  InventoryMovementEntry copyWith(
          {String? id,
          String? workOrderId,
          String? itemId,
          double? quantity,
          String? kind,
          DateTime? occurredAt}) =>
      InventoryMovementEntry(
        id: id ?? this.id,
        workOrderId: workOrderId ?? this.workOrderId,
        itemId: itemId ?? this.itemId,
        quantity: quantity ?? this.quantity,
        kind: kind ?? this.kind,
        occurredAt: occurredAt ?? this.occurredAt,
      );
  InventoryMovementEntry copyWithCompanion(
      InventoryMovementEntriesCompanion data) {
    return InventoryMovementEntry(
      id: data.id.present ? data.id.value : this.id,
      workOrderId:
          data.workOrderId.present ? data.workOrderId.value : this.workOrderId,
      itemId: data.itemId.present ? data.itemId.value : this.itemId,
      quantity: data.quantity.present ? data.quantity.value : this.quantity,
      kind: data.kind.present ? data.kind.value : this.kind,
      occurredAt:
          data.occurredAt.present ? data.occurredAt.value : this.occurredAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('InventoryMovementEntry(')
          ..write('id: $id, ')
          ..write('workOrderId: $workOrderId, ')
          ..write('itemId: $itemId, ')
          ..write('quantity: $quantity, ')
          ..write('kind: $kind, ')
          ..write('occurredAt: $occurredAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode =>
      Object.hash(id, workOrderId, itemId, quantity, kind, occurredAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is InventoryMovementEntry &&
          other.id == this.id &&
          other.workOrderId == this.workOrderId &&
          other.itemId == this.itemId &&
          other.quantity == this.quantity &&
          other.kind == this.kind &&
          other.occurredAt == this.occurredAt);
}

class InventoryMovementEntriesCompanion
    extends UpdateCompanion<InventoryMovementEntry> {
  final Value<String> id;
  final Value<String> workOrderId;
  final Value<String> itemId;
  final Value<double> quantity;
  final Value<String> kind;
  final Value<DateTime> occurredAt;
  final Value<int> rowid;
  const InventoryMovementEntriesCompanion({
    this.id = const Value.absent(),
    this.workOrderId = const Value.absent(),
    this.itemId = const Value.absent(),
    this.quantity = const Value.absent(),
    this.kind = const Value.absent(),
    this.occurredAt = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  InventoryMovementEntriesCompanion.insert({
    required String id,
    required String workOrderId,
    required String itemId,
    required double quantity,
    required String kind,
    required DateTime occurredAt,
    this.rowid = const Value.absent(),
  })  : id = Value(id),
        workOrderId = Value(workOrderId),
        itemId = Value(itemId),
        quantity = Value(quantity),
        kind = Value(kind),
        occurredAt = Value(occurredAt);
  static Insertable<InventoryMovementEntry> custom({
    Expression<String>? id,
    Expression<String>? workOrderId,
    Expression<String>? itemId,
    Expression<double>? quantity,
    Expression<String>? kind,
    Expression<DateTime>? occurredAt,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (workOrderId != null) 'work_order_id': workOrderId,
      if (itemId != null) 'item_id': itemId,
      if (quantity != null) 'quantity': quantity,
      if (kind != null) 'kind': kind,
      if (occurredAt != null) 'occurred_at': occurredAt,
      if (rowid != null) 'rowid': rowid,
    });
  }

  InventoryMovementEntriesCompanion copyWith(
      {Value<String>? id,
      Value<String>? workOrderId,
      Value<String>? itemId,
      Value<double>? quantity,
      Value<String>? kind,
      Value<DateTime>? occurredAt,
      Value<int>? rowid}) {
    return InventoryMovementEntriesCompanion(
      id: id ?? this.id,
      workOrderId: workOrderId ?? this.workOrderId,
      itemId: itemId ?? this.itemId,
      quantity: quantity ?? this.quantity,
      kind: kind ?? this.kind,
      occurredAt: occurredAt ?? this.occurredAt,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (workOrderId.present) {
      map['work_order_id'] = Variable<String>(workOrderId.value);
    }
    if (itemId.present) {
      map['item_id'] = Variable<String>(itemId.value);
    }
    if (quantity.present) {
      map['quantity'] = Variable<double>(quantity.value);
    }
    if (kind.present) {
      map['kind'] = Variable<String>(kind.value);
    }
    if (occurredAt.present) {
      map['occurred_at'] = Variable<DateTime>(occurredAt.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('InventoryMovementEntriesCompanion(')
          ..write('id: $id, ')
          ..write('workOrderId: $workOrderId, ')
          ..write('itemId: $itemId, ')
          ..write('quantity: $quantity, ')
          ..write('kind: $kind, ')
          ..write('occurredAt: $occurredAt, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $AppSettingEntriesTable extends AppSettingEntries
    with TableInfo<$AppSettingEntriesTable, AppSettingEntry> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $AppSettingEntriesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _keyMeta = const VerificationMeta('key');
  @override
  late final GeneratedColumn<String> key = GeneratedColumn<String>(
      'key', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  static const VerificationMeta _valueMeta = const VerificationMeta('value');
  @override
  late final GeneratedColumn<String> value = GeneratedColumn<String>(
      'value', aliasedName, false,
      type: DriftSqlType.string, requiredDuringInsert: true);
  @override
  List<GeneratedColumn> get $columns => [key, value];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'app_setting_entries';
  @override
  VerificationContext validateIntegrity(Insertable<AppSettingEntry> instance,
      {bool isInserting = false}) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('key')) {
      context.handle(
          _keyMeta, key.isAcceptableOrUnknown(data['key']!, _keyMeta));
    } else if (isInserting) {
      context.missing(_keyMeta);
    }
    if (data.containsKey('value')) {
      context.handle(
          _valueMeta, value.isAcceptableOrUnknown(data['value']!, _valueMeta));
    } else if (isInserting) {
      context.missing(_valueMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {key};
  @override
  AppSettingEntry map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return AppSettingEntry(
      key: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}key'])!,
      value: attachedDatabase.typeMapping
          .read(DriftSqlType.string, data['${effectivePrefix}value'])!,
    );
  }

  @override
  $AppSettingEntriesTable createAlias(String alias) {
    return $AppSettingEntriesTable(attachedDatabase, alias);
  }
}

class AppSettingEntry extends DataClass implements Insertable<AppSettingEntry> {
  final String key;
  final String value;
  const AppSettingEntry({required this.key, required this.value});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['key'] = Variable<String>(key);
    map['value'] = Variable<String>(value);
    return map;
  }

  AppSettingEntriesCompanion toCompanion(bool nullToAbsent) {
    return AppSettingEntriesCompanion(
      key: Value(key),
      value: Value(value),
    );
  }

  factory AppSettingEntry.fromJson(Map<String, dynamic> json,
      {ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return AppSettingEntry(
      key: serializer.fromJson<String>(json['key']),
      value: serializer.fromJson<String>(json['value']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'key': serializer.toJson<String>(key),
      'value': serializer.toJson<String>(value),
    };
  }

  AppSettingEntry copyWith({String? key, String? value}) => AppSettingEntry(
        key: key ?? this.key,
        value: value ?? this.value,
      );
  AppSettingEntry copyWithCompanion(AppSettingEntriesCompanion data) {
    return AppSettingEntry(
      key: data.key.present ? data.key.value : this.key,
      value: data.value.present ? data.value.value : this.value,
    );
  }

  @override
  String toString() {
    return (StringBuffer('AppSettingEntry(')
          ..write('key: $key, ')
          ..write('value: $value')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(key, value);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is AppSettingEntry &&
          other.key == this.key &&
          other.value == this.value);
}

class AppSettingEntriesCompanion extends UpdateCompanion<AppSettingEntry> {
  final Value<String> key;
  final Value<String> value;
  final Value<int> rowid;
  const AppSettingEntriesCompanion({
    this.key = const Value.absent(),
    this.value = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  AppSettingEntriesCompanion.insert({
    required String key,
    required String value,
    this.rowid = const Value.absent(),
  })  : key = Value(key),
        value = Value(value);
  static Insertable<AppSettingEntry> custom({
    Expression<String>? key,
    Expression<String>? value,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (key != null) 'key': key,
      if (value != null) 'value': value,
      if (rowid != null) 'rowid': rowid,
    });
  }

  AppSettingEntriesCompanion copyWith(
      {Value<String>? key, Value<String>? value, Value<int>? rowid}) {
    return AppSettingEntriesCompanion(
      key: key ?? this.key,
      value: value ?? this.value,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (key.present) {
      map['key'] = Variable<String>(key.value);
    }
    if (value.present) {
      map['value'] = Variable<String>(value.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('AppSettingEntriesCompanion(')
          ..write('key: $key, ')
          ..write('value: $value, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

abstract class _$WorkOrderDatabase extends GeneratedDatabase {
  _$WorkOrderDatabase(QueryExecutor e) : super(e);
  $WorkOrderDatabaseManager get managers => $WorkOrderDatabaseManager(this);
  late final $CachedWorkOrdersTable cachedWorkOrders =
      $CachedWorkOrdersTable(this);
  late final $SyncQueueEntriesTable syncQueueEntries =
      $SyncQueueEntriesTable(this);
  late final $WorkOrderTransitionEntriesTable workOrderTransitionEntries =
      $WorkOrderTransitionEntriesTable(this);
  late final $EvidenceEntriesTable evidenceEntries =
      $EvidenceEntriesTable(this);
  late final $EquipmentScanEntriesTable equipmentScanEntries =
      $EquipmentScanEntriesTable(this);
  late final $InventoryItemEntriesTable inventoryItemEntries =
      $InventoryItemEntriesTable(this);
  late final $InventoryMovementEntriesTable inventoryMovementEntries =
      $InventoryMovementEntriesTable(this);
  late final $AppSettingEntriesTable appSettingEntries =
      $AppSettingEntriesTable(this);
  @override
  Iterable<TableInfo<Table, Object?>> get allTables =>
      allSchemaEntities.whereType<TableInfo<Table, Object?>>();
  @override
  List<DatabaseSchemaEntity> get allSchemaEntities => [
        cachedWorkOrders,
        syncQueueEntries,
        workOrderTransitionEntries,
        evidenceEntries,
        equipmentScanEntries,
        inventoryItemEntries,
        inventoryMovementEntries,
        appSettingEntries
      ];
}

typedef $$CachedWorkOrdersTableCreateCompanionBuilder
    = CachedWorkOrdersCompanion Function({
  required String id,
  required String code,
  required String customerName,
  required String address,
  required String status,
  required int version,
  Value<double?> latitude,
  Value<double?> longitude,
  Value<String> priority,
  Value<DateTime?> scheduledAt,
  required DateTime updatedAt,
  Value<int> rowid,
});
typedef $$CachedWorkOrdersTableUpdateCompanionBuilder
    = CachedWorkOrdersCompanion Function({
  Value<String> id,
  Value<String> code,
  Value<String> customerName,
  Value<String> address,
  Value<String> status,
  Value<int> version,
  Value<double?> latitude,
  Value<double?> longitude,
  Value<String> priority,
  Value<DateTime?> scheduledAt,
  Value<DateTime> updatedAt,
  Value<int> rowid,
});

class $$CachedWorkOrdersTableFilterComposer
    extends Composer<_$WorkOrderDatabase, $CachedWorkOrdersTable> {
  $$CachedWorkOrdersTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get code => $composableBuilder(
      column: $table.code, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get customerName => $composableBuilder(
      column: $table.customerName, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get address => $composableBuilder(
      column: $table.address, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get status => $composableBuilder(
      column: $table.status, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get version => $composableBuilder(
      column: $table.version, builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get latitude => $composableBuilder(
      column: $table.latitude, builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get longitude => $composableBuilder(
      column: $table.longitude, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get priority => $composableBuilder(
      column: $table.priority, builder: (column) => ColumnFilters(column));

  ColumnFilters<DateTime> get scheduledAt => $composableBuilder(
      column: $table.scheduledAt, builder: (column) => ColumnFilters(column));

  ColumnFilters<DateTime> get updatedAt => $composableBuilder(
      column: $table.updatedAt, builder: (column) => ColumnFilters(column));
}

class $$CachedWorkOrdersTableOrderingComposer
    extends Composer<_$WorkOrderDatabase, $CachedWorkOrdersTable> {
  $$CachedWorkOrdersTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get code => $composableBuilder(
      column: $table.code, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get customerName => $composableBuilder(
      column: $table.customerName,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get address => $composableBuilder(
      column: $table.address, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get status => $composableBuilder(
      column: $table.status, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get version => $composableBuilder(
      column: $table.version, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get latitude => $composableBuilder(
      column: $table.latitude, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get longitude => $composableBuilder(
      column: $table.longitude, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get priority => $composableBuilder(
      column: $table.priority, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<DateTime> get scheduledAt => $composableBuilder(
      column: $table.scheduledAt, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<DateTime> get updatedAt => $composableBuilder(
      column: $table.updatedAt, builder: (column) => ColumnOrderings(column));
}

class $$CachedWorkOrdersTableAnnotationComposer
    extends Composer<_$WorkOrderDatabase, $CachedWorkOrdersTable> {
  $$CachedWorkOrdersTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get code =>
      $composableBuilder(column: $table.code, builder: (column) => column);

  GeneratedColumn<String> get customerName => $composableBuilder(
      column: $table.customerName, builder: (column) => column);

  GeneratedColumn<String> get address =>
      $composableBuilder(column: $table.address, builder: (column) => column);

  GeneratedColumn<String> get status =>
      $composableBuilder(column: $table.status, builder: (column) => column);

  GeneratedColumn<int> get version =>
      $composableBuilder(column: $table.version, builder: (column) => column);

  GeneratedColumn<double> get latitude =>
      $composableBuilder(column: $table.latitude, builder: (column) => column);

  GeneratedColumn<double> get longitude =>
      $composableBuilder(column: $table.longitude, builder: (column) => column);

  GeneratedColumn<String> get priority =>
      $composableBuilder(column: $table.priority, builder: (column) => column);

  GeneratedColumn<DateTime> get scheduledAt => $composableBuilder(
      column: $table.scheduledAt, builder: (column) => column);

  GeneratedColumn<DateTime> get updatedAt =>
      $composableBuilder(column: $table.updatedAt, builder: (column) => column);
}

class $$CachedWorkOrdersTableTableManager extends RootTableManager<
    _$WorkOrderDatabase,
    $CachedWorkOrdersTable,
    CachedWorkOrder,
    $$CachedWorkOrdersTableFilterComposer,
    $$CachedWorkOrdersTableOrderingComposer,
    $$CachedWorkOrdersTableAnnotationComposer,
    $$CachedWorkOrdersTableCreateCompanionBuilder,
    $$CachedWorkOrdersTableUpdateCompanionBuilder,
    (
      CachedWorkOrder,
      BaseReferences<_$WorkOrderDatabase, $CachedWorkOrdersTable,
          CachedWorkOrder>
    ),
    CachedWorkOrder,
    PrefetchHooks Function()> {
  $$CachedWorkOrdersTableTableManager(
      _$WorkOrderDatabase db, $CachedWorkOrdersTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$CachedWorkOrdersTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$CachedWorkOrdersTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$CachedWorkOrdersTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback: ({
            Value<String> id = const Value.absent(),
            Value<String> code = const Value.absent(),
            Value<String> customerName = const Value.absent(),
            Value<String> address = const Value.absent(),
            Value<String> status = const Value.absent(),
            Value<int> version = const Value.absent(),
            Value<double?> latitude = const Value.absent(),
            Value<double?> longitude = const Value.absent(),
            Value<String> priority = const Value.absent(),
            Value<DateTime?> scheduledAt = const Value.absent(),
            Value<DateTime> updatedAt = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              CachedWorkOrdersCompanion(
            id: id,
            code: code,
            customerName: customerName,
            address: address,
            status: status,
            version: version,
            latitude: latitude,
            longitude: longitude,
            priority: priority,
            scheduledAt: scheduledAt,
            updatedAt: updatedAt,
            rowid: rowid,
          ),
          createCompanionCallback: ({
            required String id,
            required String code,
            required String customerName,
            required String address,
            required String status,
            required int version,
            Value<double?> latitude = const Value.absent(),
            Value<double?> longitude = const Value.absent(),
            Value<String> priority = const Value.absent(),
            Value<DateTime?> scheduledAt = const Value.absent(),
            required DateTime updatedAt,
            Value<int> rowid = const Value.absent(),
          }) =>
              CachedWorkOrdersCompanion.insert(
            id: id,
            code: code,
            customerName: customerName,
            address: address,
            status: status,
            version: version,
            latitude: latitude,
            longitude: longitude,
            priority: priority,
            scheduledAt: scheduledAt,
            updatedAt: updatedAt,
            rowid: rowid,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$CachedWorkOrdersTableProcessedTableManager = ProcessedTableManager<
    _$WorkOrderDatabase,
    $CachedWorkOrdersTable,
    CachedWorkOrder,
    $$CachedWorkOrdersTableFilterComposer,
    $$CachedWorkOrdersTableOrderingComposer,
    $$CachedWorkOrdersTableAnnotationComposer,
    $$CachedWorkOrdersTableCreateCompanionBuilder,
    $$CachedWorkOrdersTableUpdateCompanionBuilder,
    (
      CachedWorkOrder,
      BaseReferences<_$WorkOrderDatabase, $CachedWorkOrdersTable,
          CachedWorkOrder>
    ),
    CachedWorkOrder,
    PrefetchHooks Function()>;
typedef $$SyncQueueEntriesTableCreateCompanionBuilder
    = SyncQueueEntriesCompanion Function({
  required String operationId,
  required String entityType,
  required String entityId,
  required String kind,
  Value<int?> baseVersion,
  required DateTime occurredAt,
  required String payloadJson,
  Value<String> state,
  Value<int> attempts,
  Value<String?> lastError,
  Value<int> rowid,
});
typedef $$SyncQueueEntriesTableUpdateCompanionBuilder
    = SyncQueueEntriesCompanion Function({
  Value<String> operationId,
  Value<String> entityType,
  Value<String> entityId,
  Value<String> kind,
  Value<int?> baseVersion,
  Value<DateTime> occurredAt,
  Value<String> payloadJson,
  Value<String> state,
  Value<int> attempts,
  Value<String?> lastError,
  Value<int> rowid,
});

class $$SyncQueueEntriesTableFilterComposer
    extends Composer<_$WorkOrderDatabase, $SyncQueueEntriesTable> {
  $$SyncQueueEntriesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get operationId => $composableBuilder(
      column: $table.operationId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get entityType => $composableBuilder(
      column: $table.entityType, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get entityId => $composableBuilder(
      column: $table.entityId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get kind => $composableBuilder(
      column: $table.kind, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get baseVersion => $composableBuilder(
      column: $table.baseVersion, builder: (column) => ColumnFilters(column));

  ColumnFilters<DateTime> get occurredAt => $composableBuilder(
      column: $table.occurredAt, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get payloadJson => $composableBuilder(
      column: $table.payloadJson, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get state => $composableBuilder(
      column: $table.state, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get attempts => $composableBuilder(
      column: $table.attempts, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get lastError => $composableBuilder(
      column: $table.lastError, builder: (column) => ColumnFilters(column));
}

class $$SyncQueueEntriesTableOrderingComposer
    extends Composer<_$WorkOrderDatabase, $SyncQueueEntriesTable> {
  $$SyncQueueEntriesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get operationId => $composableBuilder(
      column: $table.operationId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get entityType => $composableBuilder(
      column: $table.entityType, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get entityId => $composableBuilder(
      column: $table.entityId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get kind => $composableBuilder(
      column: $table.kind, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get baseVersion => $composableBuilder(
      column: $table.baseVersion, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<DateTime> get occurredAt => $composableBuilder(
      column: $table.occurredAt, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get payloadJson => $composableBuilder(
      column: $table.payloadJson, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get state => $composableBuilder(
      column: $table.state, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get attempts => $composableBuilder(
      column: $table.attempts, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get lastError => $composableBuilder(
      column: $table.lastError, builder: (column) => ColumnOrderings(column));
}

class $$SyncQueueEntriesTableAnnotationComposer
    extends Composer<_$WorkOrderDatabase, $SyncQueueEntriesTable> {
  $$SyncQueueEntriesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get operationId => $composableBuilder(
      column: $table.operationId, builder: (column) => column);

  GeneratedColumn<String> get entityType => $composableBuilder(
      column: $table.entityType, builder: (column) => column);

  GeneratedColumn<String> get entityId =>
      $composableBuilder(column: $table.entityId, builder: (column) => column);

  GeneratedColumn<String> get kind =>
      $composableBuilder(column: $table.kind, builder: (column) => column);

  GeneratedColumn<int> get baseVersion => $composableBuilder(
      column: $table.baseVersion, builder: (column) => column);

  GeneratedColumn<DateTime> get occurredAt => $composableBuilder(
      column: $table.occurredAt, builder: (column) => column);

  GeneratedColumn<String> get payloadJson => $composableBuilder(
      column: $table.payloadJson, builder: (column) => column);

  GeneratedColumn<String> get state =>
      $composableBuilder(column: $table.state, builder: (column) => column);

  GeneratedColumn<int> get attempts =>
      $composableBuilder(column: $table.attempts, builder: (column) => column);

  GeneratedColumn<String> get lastError =>
      $composableBuilder(column: $table.lastError, builder: (column) => column);
}

class $$SyncQueueEntriesTableTableManager extends RootTableManager<
    _$WorkOrderDatabase,
    $SyncQueueEntriesTable,
    SyncQueueEntry,
    $$SyncQueueEntriesTableFilterComposer,
    $$SyncQueueEntriesTableOrderingComposer,
    $$SyncQueueEntriesTableAnnotationComposer,
    $$SyncQueueEntriesTableCreateCompanionBuilder,
    $$SyncQueueEntriesTableUpdateCompanionBuilder,
    (
      SyncQueueEntry,
      BaseReferences<_$WorkOrderDatabase, $SyncQueueEntriesTable,
          SyncQueueEntry>
    ),
    SyncQueueEntry,
    PrefetchHooks Function()> {
  $$SyncQueueEntriesTableTableManager(
      _$WorkOrderDatabase db, $SyncQueueEntriesTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$SyncQueueEntriesTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$SyncQueueEntriesTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$SyncQueueEntriesTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback: ({
            Value<String> operationId = const Value.absent(),
            Value<String> entityType = const Value.absent(),
            Value<String> entityId = const Value.absent(),
            Value<String> kind = const Value.absent(),
            Value<int?> baseVersion = const Value.absent(),
            Value<DateTime> occurredAt = const Value.absent(),
            Value<String> payloadJson = const Value.absent(),
            Value<String> state = const Value.absent(),
            Value<int> attempts = const Value.absent(),
            Value<String?> lastError = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              SyncQueueEntriesCompanion(
            operationId: operationId,
            entityType: entityType,
            entityId: entityId,
            kind: kind,
            baseVersion: baseVersion,
            occurredAt: occurredAt,
            payloadJson: payloadJson,
            state: state,
            attempts: attempts,
            lastError: lastError,
            rowid: rowid,
          ),
          createCompanionCallback: ({
            required String operationId,
            required String entityType,
            required String entityId,
            required String kind,
            Value<int?> baseVersion = const Value.absent(),
            required DateTime occurredAt,
            required String payloadJson,
            Value<String> state = const Value.absent(),
            Value<int> attempts = const Value.absent(),
            Value<String?> lastError = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              SyncQueueEntriesCompanion.insert(
            operationId: operationId,
            entityType: entityType,
            entityId: entityId,
            kind: kind,
            baseVersion: baseVersion,
            occurredAt: occurredAt,
            payloadJson: payloadJson,
            state: state,
            attempts: attempts,
            lastError: lastError,
            rowid: rowid,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$SyncQueueEntriesTableProcessedTableManager = ProcessedTableManager<
    _$WorkOrderDatabase,
    $SyncQueueEntriesTable,
    SyncQueueEntry,
    $$SyncQueueEntriesTableFilterComposer,
    $$SyncQueueEntriesTableOrderingComposer,
    $$SyncQueueEntriesTableAnnotationComposer,
    $$SyncQueueEntriesTableCreateCompanionBuilder,
    $$SyncQueueEntriesTableUpdateCompanionBuilder,
    (
      SyncQueueEntry,
      BaseReferences<_$WorkOrderDatabase, $SyncQueueEntriesTable,
          SyncQueueEntry>
    ),
    SyncQueueEntry,
    PrefetchHooks Function()>;
typedef $$WorkOrderTransitionEntriesTableCreateCompanionBuilder
    = WorkOrderTransitionEntriesCompanion Function({
  required String operationId,
  required String workOrderId,
  required String fromStatus,
  required String toStatus,
  Value<String?> note,
  Value<double?> latitude,
  Value<double?> longitude,
  required DateTime occurredAt,
  Value<int> rowid,
});
typedef $$WorkOrderTransitionEntriesTableUpdateCompanionBuilder
    = WorkOrderTransitionEntriesCompanion Function({
  Value<String> operationId,
  Value<String> workOrderId,
  Value<String> fromStatus,
  Value<String> toStatus,
  Value<String?> note,
  Value<double?> latitude,
  Value<double?> longitude,
  Value<DateTime> occurredAt,
  Value<int> rowid,
});

class $$WorkOrderTransitionEntriesTableFilterComposer
    extends Composer<_$WorkOrderDatabase, $WorkOrderTransitionEntriesTable> {
  $$WorkOrderTransitionEntriesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get operationId => $composableBuilder(
      column: $table.operationId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get workOrderId => $composableBuilder(
      column: $table.workOrderId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get fromStatus => $composableBuilder(
      column: $table.fromStatus, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get toStatus => $composableBuilder(
      column: $table.toStatus, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get note => $composableBuilder(
      column: $table.note, builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get latitude => $composableBuilder(
      column: $table.latitude, builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get longitude => $composableBuilder(
      column: $table.longitude, builder: (column) => ColumnFilters(column));

  ColumnFilters<DateTime> get occurredAt => $composableBuilder(
      column: $table.occurredAt, builder: (column) => ColumnFilters(column));
}

class $$WorkOrderTransitionEntriesTableOrderingComposer
    extends Composer<_$WorkOrderDatabase, $WorkOrderTransitionEntriesTable> {
  $$WorkOrderTransitionEntriesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get operationId => $composableBuilder(
      column: $table.operationId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get workOrderId => $composableBuilder(
      column: $table.workOrderId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get fromStatus => $composableBuilder(
      column: $table.fromStatus, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get toStatus => $composableBuilder(
      column: $table.toStatus, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get note => $composableBuilder(
      column: $table.note, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get latitude => $composableBuilder(
      column: $table.latitude, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get longitude => $composableBuilder(
      column: $table.longitude, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<DateTime> get occurredAt => $composableBuilder(
      column: $table.occurredAt, builder: (column) => ColumnOrderings(column));
}

class $$WorkOrderTransitionEntriesTableAnnotationComposer
    extends Composer<_$WorkOrderDatabase, $WorkOrderTransitionEntriesTable> {
  $$WorkOrderTransitionEntriesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get operationId => $composableBuilder(
      column: $table.operationId, builder: (column) => column);

  GeneratedColumn<String> get workOrderId => $composableBuilder(
      column: $table.workOrderId, builder: (column) => column);

  GeneratedColumn<String> get fromStatus => $composableBuilder(
      column: $table.fromStatus, builder: (column) => column);

  GeneratedColumn<String> get toStatus =>
      $composableBuilder(column: $table.toStatus, builder: (column) => column);

  GeneratedColumn<String> get note =>
      $composableBuilder(column: $table.note, builder: (column) => column);

  GeneratedColumn<double> get latitude =>
      $composableBuilder(column: $table.latitude, builder: (column) => column);

  GeneratedColumn<double> get longitude =>
      $composableBuilder(column: $table.longitude, builder: (column) => column);

  GeneratedColumn<DateTime> get occurredAt => $composableBuilder(
      column: $table.occurredAt, builder: (column) => column);
}

class $$WorkOrderTransitionEntriesTableTableManager extends RootTableManager<
    _$WorkOrderDatabase,
    $WorkOrderTransitionEntriesTable,
    WorkOrderTransitionEntry,
    $$WorkOrderTransitionEntriesTableFilterComposer,
    $$WorkOrderTransitionEntriesTableOrderingComposer,
    $$WorkOrderTransitionEntriesTableAnnotationComposer,
    $$WorkOrderTransitionEntriesTableCreateCompanionBuilder,
    $$WorkOrderTransitionEntriesTableUpdateCompanionBuilder,
    (
      WorkOrderTransitionEntry,
      BaseReferences<_$WorkOrderDatabase, $WorkOrderTransitionEntriesTable,
          WorkOrderTransitionEntry>
    ),
    WorkOrderTransitionEntry,
    PrefetchHooks Function()> {
  $$WorkOrderTransitionEntriesTableTableManager(
      _$WorkOrderDatabase db, $WorkOrderTransitionEntriesTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$WorkOrderTransitionEntriesTableFilterComposer(
                  $db: db, $table: table),
          createOrderingComposer: () =>
              $$WorkOrderTransitionEntriesTableOrderingComposer(
                  $db: db, $table: table),
          createComputedFieldComposer: () =>
              $$WorkOrderTransitionEntriesTableAnnotationComposer(
                  $db: db, $table: table),
          updateCompanionCallback: ({
            Value<String> operationId = const Value.absent(),
            Value<String> workOrderId = const Value.absent(),
            Value<String> fromStatus = const Value.absent(),
            Value<String> toStatus = const Value.absent(),
            Value<String?> note = const Value.absent(),
            Value<double?> latitude = const Value.absent(),
            Value<double?> longitude = const Value.absent(),
            Value<DateTime> occurredAt = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              WorkOrderTransitionEntriesCompanion(
            operationId: operationId,
            workOrderId: workOrderId,
            fromStatus: fromStatus,
            toStatus: toStatus,
            note: note,
            latitude: latitude,
            longitude: longitude,
            occurredAt: occurredAt,
            rowid: rowid,
          ),
          createCompanionCallback: ({
            required String operationId,
            required String workOrderId,
            required String fromStatus,
            required String toStatus,
            Value<String?> note = const Value.absent(),
            Value<double?> latitude = const Value.absent(),
            Value<double?> longitude = const Value.absent(),
            required DateTime occurredAt,
            Value<int> rowid = const Value.absent(),
          }) =>
              WorkOrderTransitionEntriesCompanion.insert(
            operationId: operationId,
            workOrderId: workOrderId,
            fromStatus: fromStatus,
            toStatus: toStatus,
            note: note,
            latitude: latitude,
            longitude: longitude,
            occurredAt: occurredAt,
            rowid: rowid,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$WorkOrderTransitionEntriesTableProcessedTableManager
    = ProcessedTableManager<
        _$WorkOrderDatabase,
        $WorkOrderTransitionEntriesTable,
        WorkOrderTransitionEntry,
        $$WorkOrderTransitionEntriesTableFilterComposer,
        $$WorkOrderTransitionEntriesTableOrderingComposer,
        $$WorkOrderTransitionEntriesTableAnnotationComposer,
        $$WorkOrderTransitionEntriesTableCreateCompanionBuilder,
        $$WorkOrderTransitionEntriesTableUpdateCompanionBuilder,
        (
          WorkOrderTransitionEntry,
          BaseReferences<_$WorkOrderDatabase, $WorkOrderTransitionEntriesTable,
              WorkOrderTransitionEntry>
        ),
        WorkOrderTransitionEntry,
        PrefetchHooks Function()>;
typedef $$EvidenceEntriesTableCreateCompanionBuilder = EvidenceEntriesCompanion
    Function({
  required String id,
  required String workOrderId,
  required String category,
  required String localPath,
  required String sha256,
  Value<String> state,
  required DateTime createdAt,
  Value<int> rowid,
});
typedef $$EvidenceEntriesTableUpdateCompanionBuilder = EvidenceEntriesCompanion
    Function({
  Value<String> id,
  Value<String> workOrderId,
  Value<String> category,
  Value<String> localPath,
  Value<String> sha256,
  Value<String> state,
  Value<DateTime> createdAt,
  Value<int> rowid,
});

class $$EvidenceEntriesTableFilterComposer
    extends Composer<_$WorkOrderDatabase, $EvidenceEntriesTable> {
  $$EvidenceEntriesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get workOrderId => $composableBuilder(
      column: $table.workOrderId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get category => $composableBuilder(
      column: $table.category, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get localPath => $composableBuilder(
      column: $table.localPath, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get sha256 => $composableBuilder(
      column: $table.sha256, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get state => $composableBuilder(
      column: $table.state, builder: (column) => ColumnFilters(column));

  ColumnFilters<DateTime> get createdAt => $composableBuilder(
      column: $table.createdAt, builder: (column) => ColumnFilters(column));
}

class $$EvidenceEntriesTableOrderingComposer
    extends Composer<_$WorkOrderDatabase, $EvidenceEntriesTable> {
  $$EvidenceEntriesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get workOrderId => $composableBuilder(
      column: $table.workOrderId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get category => $composableBuilder(
      column: $table.category, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get localPath => $composableBuilder(
      column: $table.localPath, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get sha256 => $composableBuilder(
      column: $table.sha256, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get state => $composableBuilder(
      column: $table.state, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<DateTime> get createdAt => $composableBuilder(
      column: $table.createdAt, builder: (column) => ColumnOrderings(column));
}

class $$EvidenceEntriesTableAnnotationComposer
    extends Composer<_$WorkOrderDatabase, $EvidenceEntriesTable> {
  $$EvidenceEntriesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get workOrderId => $composableBuilder(
      column: $table.workOrderId, builder: (column) => column);

  GeneratedColumn<String> get category =>
      $composableBuilder(column: $table.category, builder: (column) => column);

  GeneratedColumn<String> get localPath =>
      $composableBuilder(column: $table.localPath, builder: (column) => column);

  GeneratedColumn<String> get sha256 =>
      $composableBuilder(column: $table.sha256, builder: (column) => column);

  GeneratedColumn<String> get state =>
      $composableBuilder(column: $table.state, builder: (column) => column);

  GeneratedColumn<DateTime> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);
}

class $$EvidenceEntriesTableTableManager extends RootTableManager<
    _$WorkOrderDatabase,
    $EvidenceEntriesTable,
    EvidenceEntry,
    $$EvidenceEntriesTableFilterComposer,
    $$EvidenceEntriesTableOrderingComposer,
    $$EvidenceEntriesTableAnnotationComposer,
    $$EvidenceEntriesTableCreateCompanionBuilder,
    $$EvidenceEntriesTableUpdateCompanionBuilder,
    (
      EvidenceEntry,
      BaseReferences<_$WorkOrderDatabase, $EvidenceEntriesTable, EvidenceEntry>
    ),
    EvidenceEntry,
    PrefetchHooks Function()> {
  $$EvidenceEntriesTableTableManager(
      _$WorkOrderDatabase db, $EvidenceEntriesTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$EvidenceEntriesTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$EvidenceEntriesTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$EvidenceEntriesTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback: ({
            Value<String> id = const Value.absent(),
            Value<String> workOrderId = const Value.absent(),
            Value<String> category = const Value.absent(),
            Value<String> localPath = const Value.absent(),
            Value<String> sha256 = const Value.absent(),
            Value<String> state = const Value.absent(),
            Value<DateTime> createdAt = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              EvidenceEntriesCompanion(
            id: id,
            workOrderId: workOrderId,
            category: category,
            localPath: localPath,
            sha256: sha256,
            state: state,
            createdAt: createdAt,
            rowid: rowid,
          ),
          createCompanionCallback: ({
            required String id,
            required String workOrderId,
            required String category,
            required String localPath,
            required String sha256,
            Value<String> state = const Value.absent(),
            required DateTime createdAt,
            Value<int> rowid = const Value.absent(),
          }) =>
              EvidenceEntriesCompanion.insert(
            id: id,
            workOrderId: workOrderId,
            category: category,
            localPath: localPath,
            sha256: sha256,
            state: state,
            createdAt: createdAt,
            rowid: rowid,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$EvidenceEntriesTableProcessedTableManager = ProcessedTableManager<
    _$WorkOrderDatabase,
    $EvidenceEntriesTable,
    EvidenceEntry,
    $$EvidenceEntriesTableFilterComposer,
    $$EvidenceEntriesTableOrderingComposer,
    $$EvidenceEntriesTableAnnotationComposer,
    $$EvidenceEntriesTableCreateCompanionBuilder,
    $$EvidenceEntriesTableUpdateCompanionBuilder,
    (
      EvidenceEntry,
      BaseReferences<_$WorkOrderDatabase, $EvidenceEntriesTable, EvidenceEntry>
    ),
    EvidenceEntry,
    PrefetchHooks Function()>;
typedef $$EquipmentScanEntriesTableCreateCompanionBuilder
    = EquipmentScanEntriesCompanion Function({
  required String id,
  required String workOrderId,
  required String serial,
  Value<String> state,
  required DateTime createdAt,
  Value<int> rowid,
});
typedef $$EquipmentScanEntriesTableUpdateCompanionBuilder
    = EquipmentScanEntriesCompanion Function({
  Value<String> id,
  Value<String> workOrderId,
  Value<String> serial,
  Value<String> state,
  Value<DateTime> createdAt,
  Value<int> rowid,
});

class $$EquipmentScanEntriesTableFilterComposer
    extends Composer<_$WorkOrderDatabase, $EquipmentScanEntriesTable> {
  $$EquipmentScanEntriesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get workOrderId => $composableBuilder(
      column: $table.workOrderId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get serial => $composableBuilder(
      column: $table.serial, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get state => $composableBuilder(
      column: $table.state, builder: (column) => ColumnFilters(column));

  ColumnFilters<DateTime> get createdAt => $composableBuilder(
      column: $table.createdAt, builder: (column) => ColumnFilters(column));
}

class $$EquipmentScanEntriesTableOrderingComposer
    extends Composer<_$WorkOrderDatabase, $EquipmentScanEntriesTable> {
  $$EquipmentScanEntriesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get workOrderId => $composableBuilder(
      column: $table.workOrderId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get serial => $composableBuilder(
      column: $table.serial, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get state => $composableBuilder(
      column: $table.state, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<DateTime> get createdAt => $composableBuilder(
      column: $table.createdAt, builder: (column) => ColumnOrderings(column));
}

class $$EquipmentScanEntriesTableAnnotationComposer
    extends Composer<_$WorkOrderDatabase, $EquipmentScanEntriesTable> {
  $$EquipmentScanEntriesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get workOrderId => $composableBuilder(
      column: $table.workOrderId, builder: (column) => column);

  GeneratedColumn<String> get serial =>
      $composableBuilder(column: $table.serial, builder: (column) => column);

  GeneratedColumn<String> get state =>
      $composableBuilder(column: $table.state, builder: (column) => column);

  GeneratedColumn<DateTime> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);
}

class $$EquipmentScanEntriesTableTableManager extends RootTableManager<
    _$WorkOrderDatabase,
    $EquipmentScanEntriesTable,
    EquipmentScanEntry,
    $$EquipmentScanEntriesTableFilterComposer,
    $$EquipmentScanEntriesTableOrderingComposer,
    $$EquipmentScanEntriesTableAnnotationComposer,
    $$EquipmentScanEntriesTableCreateCompanionBuilder,
    $$EquipmentScanEntriesTableUpdateCompanionBuilder,
    (
      EquipmentScanEntry,
      BaseReferences<_$WorkOrderDatabase, $EquipmentScanEntriesTable,
          EquipmentScanEntry>
    ),
    EquipmentScanEntry,
    PrefetchHooks Function()> {
  $$EquipmentScanEntriesTableTableManager(
      _$WorkOrderDatabase db, $EquipmentScanEntriesTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$EquipmentScanEntriesTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$EquipmentScanEntriesTableOrderingComposer(
                  $db: db, $table: table),
          createComputedFieldComposer: () =>
              $$EquipmentScanEntriesTableAnnotationComposer(
                  $db: db, $table: table),
          updateCompanionCallback: ({
            Value<String> id = const Value.absent(),
            Value<String> workOrderId = const Value.absent(),
            Value<String> serial = const Value.absent(),
            Value<String> state = const Value.absent(),
            Value<DateTime> createdAt = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              EquipmentScanEntriesCompanion(
            id: id,
            workOrderId: workOrderId,
            serial: serial,
            state: state,
            createdAt: createdAt,
            rowid: rowid,
          ),
          createCompanionCallback: ({
            required String id,
            required String workOrderId,
            required String serial,
            Value<String> state = const Value.absent(),
            required DateTime createdAt,
            Value<int> rowid = const Value.absent(),
          }) =>
              EquipmentScanEntriesCompanion.insert(
            id: id,
            workOrderId: workOrderId,
            serial: serial,
            state: state,
            createdAt: createdAt,
            rowid: rowid,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$EquipmentScanEntriesTableProcessedTableManager
    = ProcessedTableManager<
        _$WorkOrderDatabase,
        $EquipmentScanEntriesTable,
        EquipmentScanEntry,
        $$EquipmentScanEntriesTableFilterComposer,
        $$EquipmentScanEntriesTableOrderingComposer,
        $$EquipmentScanEntriesTableAnnotationComposer,
        $$EquipmentScanEntriesTableCreateCompanionBuilder,
        $$EquipmentScanEntriesTableUpdateCompanionBuilder,
        (
          EquipmentScanEntry,
          BaseReferences<_$WorkOrderDatabase, $EquipmentScanEntriesTable,
              EquipmentScanEntry>
        ),
        EquipmentScanEntry,
        PrefetchHooks Function()>;
typedef $$InventoryItemEntriesTableCreateCompanionBuilder
    = InventoryItemEntriesCompanion Function({
  required String id,
  required String sku,
  required String description,
  required double quantity,
  required String unit,
  Value<String?> serialNumber,
  required int version,
  Value<int> rowid,
});
typedef $$InventoryItemEntriesTableUpdateCompanionBuilder
    = InventoryItemEntriesCompanion Function({
  Value<String> id,
  Value<String> sku,
  Value<String> description,
  Value<double> quantity,
  Value<String> unit,
  Value<String?> serialNumber,
  Value<int> version,
  Value<int> rowid,
});

class $$InventoryItemEntriesTableFilterComposer
    extends Composer<_$WorkOrderDatabase, $InventoryItemEntriesTable> {
  $$InventoryItemEntriesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get sku => $composableBuilder(
      column: $table.sku, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get description => $composableBuilder(
      column: $table.description, builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get quantity => $composableBuilder(
      column: $table.quantity, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get unit => $composableBuilder(
      column: $table.unit, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get serialNumber => $composableBuilder(
      column: $table.serialNumber, builder: (column) => ColumnFilters(column));

  ColumnFilters<int> get version => $composableBuilder(
      column: $table.version, builder: (column) => ColumnFilters(column));
}

class $$InventoryItemEntriesTableOrderingComposer
    extends Composer<_$WorkOrderDatabase, $InventoryItemEntriesTable> {
  $$InventoryItemEntriesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get sku => $composableBuilder(
      column: $table.sku, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get description => $composableBuilder(
      column: $table.description, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get quantity => $composableBuilder(
      column: $table.quantity, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get unit => $composableBuilder(
      column: $table.unit, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get serialNumber => $composableBuilder(
      column: $table.serialNumber,
      builder: (column) => ColumnOrderings(column));

  ColumnOrderings<int> get version => $composableBuilder(
      column: $table.version, builder: (column) => ColumnOrderings(column));
}

class $$InventoryItemEntriesTableAnnotationComposer
    extends Composer<_$WorkOrderDatabase, $InventoryItemEntriesTable> {
  $$InventoryItemEntriesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get sku =>
      $composableBuilder(column: $table.sku, builder: (column) => column);

  GeneratedColumn<String> get description => $composableBuilder(
      column: $table.description, builder: (column) => column);

  GeneratedColumn<double> get quantity =>
      $composableBuilder(column: $table.quantity, builder: (column) => column);

  GeneratedColumn<String> get unit =>
      $composableBuilder(column: $table.unit, builder: (column) => column);

  GeneratedColumn<String> get serialNumber => $composableBuilder(
      column: $table.serialNumber, builder: (column) => column);

  GeneratedColumn<int> get version =>
      $composableBuilder(column: $table.version, builder: (column) => column);
}

class $$InventoryItemEntriesTableTableManager extends RootTableManager<
    _$WorkOrderDatabase,
    $InventoryItemEntriesTable,
    InventoryItemEntry,
    $$InventoryItemEntriesTableFilterComposer,
    $$InventoryItemEntriesTableOrderingComposer,
    $$InventoryItemEntriesTableAnnotationComposer,
    $$InventoryItemEntriesTableCreateCompanionBuilder,
    $$InventoryItemEntriesTableUpdateCompanionBuilder,
    (
      InventoryItemEntry,
      BaseReferences<_$WorkOrderDatabase, $InventoryItemEntriesTable,
          InventoryItemEntry>
    ),
    InventoryItemEntry,
    PrefetchHooks Function()> {
  $$InventoryItemEntriesTableTableManager(
      _$WorkOrderDatabase db, $InventoryItemEntriesTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$InventoryItemEntriesTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$InventoryItemEntriesTableOrderingComposer(
                  $db: db, $table: table),
          createComputedFieldComposer: () =>
              $$InventoryItemEntriesTableAnnotationComposer(
                  $db: db, $table: table),
          updateCompanionCallback: ({
            Value<String> id = const Value.absent(),
            Value<String> sku = const Value.absent(),
            Value<String> description = const Value.absent(),
            Value<double> quantity = const Value.absent(),
            Value<String> unit = const Value.absent(),
            Value<String?> serialNumber = const Value.absent(),
            Value<int> version = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              InventoryItemEntriesCompanion(
            id: id,
            sku: sku,
            description: description,
            quantity: quantity,
            unit: unit,
            serialNumber: serialNumber,
            version: version,
            rowid: rowid,
          ),
          createCompanionCallback: ({
            required String id,
            required String sku,
            required String description,
            required double quantity,
            required String unit,
            Value<String?> serialNumber = const Value.absent(),
            required int version,
            Value<int> rowid = const Value.absent(),
          }) =>
              InventoryItemEntriesCompanion.insert(
            id: id,
            sku: sku,
            description: description,
            quantity: quantity,
            unit: unit,
            serialNumber: serialNumber,
            version: version,
            rowid: rowid,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$InventoryItemEntriesTableProcessedTableManager
    = ProcessedTableManager<
        _$WorkOrderDatabase,
        $InventoryItemEntriesTable,
        InventoryItemEntry,
        $$InventoryItemEntriesTableFilterComposer,
        $$InventoryItemEntriesTableOrderingComposer,
        $$InventoryItemEntriesTableAnnotationComposer,
        $$InventoryItemEntriesTableCreateCompanionBuilder,
        $$InventoryItemEntriesTableUpdateCompanionBuilder,
        (
          InventoryItemEntry,
          BaseReferences<_$WorkOrderDatabase, $InventoryItemEntriesTable,
              InventoryItemEntry>
        ),
        InventoryItemEntry,
        PrefetchHooks Function()>;
typedef $$InventoryMovementEntriesTableCreateCompanionBuilder
    = InventoryMovementEntriesCompanion Function({
  required String id,
  required String workOrderId,
  required String itemId,
  required double quantity,
  required String kind,
  required DateTime occurredAt,
  Value<int> rowid,
});
typedef $$InventoryMovementEntriesTableUpdateCompanionBuilder
    = InventoryMovementEntriesCompanion Function({
  Value<String> id,
  Value<String> workOrderId,
  Value<String> itemId,
  Value<double> quantity,
  Value<String> kind,
  Value<DateTime> occurredAt,
  Value<int> rowid,
});

class $$InventoryMovementEntriesTableFilterComposer
    extends Composer<_$WorkOrderDatabase, $InventoryMovementEntriesTable> {
  $$InventoryMovementEntriesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get workOrderId => $composableBuilder(
      column: $table.workOrderId, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get itemId => $composableBuilder(
      column: $table.itemId, builder: (column) => ColumnFilters(column));

  ColumnFilters<double> get quantity => $composableBuilder(
      column: $table.quantity, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get kind => $composableBuilder(
      column: $table.kind, builder: (column) => ColumnFilters(column));

  ColumnFilters<DateTime> get occurredAt => $composableBuilder(
      column: $table.occurredAt, builder: (column) => ColumnFilters(column));
}

class $$InventoryMovementEntriesTableOrderingComposer
    extends Composer<_$WorkOrderDatabase, $InventoryMovementEntriesTable> {
  $$InventoryMovementEntriesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get id => $composableBuilder(
      column: $table.id, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get workOrderId => $composableBuilder(
      column: $table.workOrderId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get itemId => $composableBuilder(
      column: $table.itemId, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<double> get quantity => $composableBuilder(
      column: $table.quantity, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get kind => $composableBuilder(
      column: $table.kind, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<DateTime> get occurredAt => $composableBuilder(
      column: $table.occurredAt, builder: (column) => ColumnOrderings(column));
}

class $$InventoryMovementEntriesTableAnnotationComposer
    extends Composer<_$WorkOrderDatabase, $InventoryMovementEntriesTable> {
  $$InventoryMovementEntriesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get workOrderId => $composableBuilder(
      column: $table.workOrderId, builder: (column) => column);

  GeneratedColumn<String> get itemId =>
      $composableBuilder(column: $table.itemId, builder: (column) => column);

  GeneratedColumn<double> get quantity =>
      $composableBuilder(column: $table.quantity, builder: (column) => column);

  GeneratedColumn<String> get kind =>
      $composableBuilder(column: $table.kind, builder: (column) => column);

  GeneratedColumn<DateTime> get occurredAt => $composableBuilder(
      column: $table.occurredAt, builder: (column) => column);
}

class $$InventoryMovementEntriesTableTableManager extends RootTableManager<
    _$WorkOrderDatabase,
    $InventoryMovementEntriesTable,
    InventoryMovementEntry,
    $$InventoryMovementEntriesTableFilterComposer,
    $$InventoryMovementEntriesTableOrderingComposer,
    $$InventoryMovementEntriesTableAnnotationComposer,
    $$InventoryMovementEntriesTableCreateCompanionBuilder,
    $$InventoryMovementEntriesTableUpdateCompanionBuilder,
    (
      InventoryMovementEntry,
      BaseReferences<_$WorkOrderDatabase, $InventoryMovementEntriesTable,
          InventoryMovementEntry>
    ),
    InventoryMovementEntry,
    PrefetchHooks Function()> {
  $$InventoryMovementEntriesTableTableManager(
      _$WorkOrderDatabase db, $InventoryMovementEntriesTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$InventoryMovementEntriesTableFilterComposer(
                  $db: db, $table: table),
          createOrderingComposer: () =>
              $$InventoryMovementEntriesTableOrderingComposer(
                  $db: db, $table: table),
          createComputedFieldComposer: () =>
              $$InventoryMovementEntriesTableAnnotationComposer(
                  $db: db, $table: table),
          updateCompanionCallback: ({
            Value<String> id = const Value.absent(),
            Value<String> workOrderId = const Value.absent(),
            Value<String> itemId = const Value.absent(),
            Value<double> quantity = const Value.absent(),
            Value<String> kind = const Value.absent(),
            Value<DateTime> occurredAt = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              InventoryMovementEntriesCompanion(
            id: id,
            workOrderId: workOrderId,
            itemId: itemId,
            quantity: quantity,
            kind: kind,
            occurredAt: occurredAt,
            rowid: rowid,
          ),
          createCompanionCallback: ({
            required String id,
            required String workOrderId,
            required String itemId,
            required double quantity,
            required String kind,
            required DateTime occurredAt,
            Value<int> rowid = const Value.absent(),
          }) =>
              InventoryMovementEntriesCompanion.insert(
            id: id,
            workOrderId: workOrderId,
            itemId: itemId,
            quantity: quantity,
            kind: kind,
            occurredAt: occurredAt,
            rowid: rowid,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$InventoryMovementEntriesTableProcessedTableManager
    = ProcessedTableManager<
        _$WorkOrderDatabase,
        $InventoryMovementEntriesTable,
        InventoryMovementEntry,
        $$InventoryMovementEntriesTableFilterComposer,
        $$InventoryMovementEntriesTableOrderingComposer,
        $$InventoryMovementEntriesTableAnnotationComposer,
        $$InventoryMovementEntriesTableCreateCompanionBuilder,
        $$InventoryMovementEntriesTableUpdateCompanionBuilder,
        (
          InventoryMovementEntry,
          BaseReferences<_$WorkOrderDatabase, $InventoryMovementEntriesTable,
              InventoryMovementEntry>
        ),
        InventoryMovementEntry,
        PrefetchHooks Function()>;
typedef $$AppSettingEntriesTableCreateCompanionBuilder
    = AppSettingEntriesCompanion Function({
  required String key,
  required String value,
  Value<int> rowid,
});
typedef $$AppSettingEntriesTableUpdateCompanionBuilder
    = AppSettingEntriesCompanion Function({
  Value<String> key,
  Value<String> value,
  Value<int> rowid,
});

class $$AppSettingEntriesTableFilterComposer
    extends Composer<_$WorkOrderDatabase, $AppSettingEntriesTable> {
  $$AppSettingEntriesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get key => $composableBuilder(
      column: $table.key, builder: (column) => ColumnFilters(column));

  ColumnFilters<String> get value => $composableBuilder(
      column: $table.value, builder: (column) => ColumnFilters(column));
}

class $$AppSettingEntriesTableOrderingComposer
    extends Composer<_$WorkOrderDatabase, $AppSettingEntriesTable> {
  $$AppSettingEntriesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get key => $composableBuilder(
      column: $table.key, builder: (column) => ColumnOrderings(column));

  ColumnOrderings<String> get value => $composableBuilder(
      column: $table.value, builder: (column) => ColumnOrderings(column));
}

class $$AppSettingEntriesTableAnnotationComposer
    extends Composer<_$WorkOrderDatabase, $AppSettingEntriesTable> {
  $$AppSettingEntriesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get key =>
      $composableBuilder(column: $table.key, builder: (column) => column);

  GeneratedColumn<String> get value =>
      $composableBuilder(column: $table.value, builder: (column) => column);
}

class $$AppSettingEntriesTableTableManager extends RootTableManager<
    _$WorkOrderDatabase,
    $AppSettingEntriesTable,
    AppSettingEntry,
    $$AppSettingEntriesTableFilterComposer,
    $$AppSettingEntriesTableOrderingComposer,
    $$AppSettingEntriesTableAnnotationComposer,
    $$AppSettingEntriesTableCreateCompanionBuilder,
    $$AppSettingEntriesTableUpdateCompanionBuilder,
    (
      AppSettingEntry,
      BaseReferences<_$WorkOrderDatabase, $AppSettingEntriesTable,
          AppSettingEntry>
    ),
    AppSettingEntry,
    PrefetchHooks Function()> {
  $$AppSettingEntriesTableTableManager(
      _$WorkOrderDatabase db, $AppSettingEntriesTable table)
      : super(TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$AppSettingEntriesTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$AppSettingEntriesTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$AppSettingEntriesTableAnnotationComposer(
                  $db: db, $table: table),
          updateCompanionCallback: ({
            Value<String> key = const Value.absent(),
            Value<String> value = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) =>
              AppSettingEntriesCompanion(
            key: key,
            value: value,
            rowid: rowid,
          ),
          createCompanionCallback: ({
            required String key,
            required String value,
            Value<int> rowid = const Value.absent(),
          }) =>
              AppSettingEntriesCompanion.insert(
            key: key,
            value: value,
            rowid: rowid,
          ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ));
}

typedef $$AppSettingEntriesTableProcessedTableManager = ProcessedTableManager<
    _$WorkOrderDatabase,
    $AppSettingEntriesTable,
    AppSettingEntry,
    $$AppSettingEntriesTableFilterComposer,
    $$AppSettingEntriesTableOrderingComposer,
    $$AppSettingEntriesTableAnnotationComposer,
    $$AppSettingEntriesTableCreateCompanionBuilder,
    $$AppSettingEntriesTableUpdateCompanionBuilder,
    (
      AppSettingEntry,
      BaseReferences<_$WorkOrderDatabase, $AppSettingEntriesTable,
          AppSettingEntry>
    ),
    AppSettingEntry,
    PrefetchHooks Function()>;

class $WorkOrderDatabaseManager {
  final _$WorkOrderDatabase _db;
  $WorkOrderDatabaseManager(this._db);
  $$CachedWorkOrdersTableTableManager get cachedWorkOrders =>
      $$CachedWorkOrdersTableTableManager(_db, _db.cachedWorkOrders);
  $$SyncQueueEntriesTableTableManager get syncQueueEntries =>
      $$SyncQueueEntriesTableTableManager(_db, _db.syncQueueEntries);
  $$WorkOrderTransitionEntriesTableTableManager
      get workOrderTransitionEntries =>
          $$WorkOrderTransitionEntriesTableTableManager(
              _db, _db.workOrderTransitionEntries);
  $$EvidenceEntriesTableTableManager get evidenceEntries =>
      $$EvidenceEntriesTableTableManager(_db, _db.evidenceEntries);
  $$EquipmentScanEntriesTableTableManager get equipmentScanEntries =>
      $$EquipmentScanEntriesTableTableManager(_db, _db.equipmentScanEntries);
  $$InventoryItemEntriesTableTableManager get inventoryItemEntries =>
      $$InventoryItemEntriesTableTableManager(_db, _db.inventoryItemEntries);
  $$InventoryMovementEntriesTableTableManager get inventoryMovementEntries =>
      $$InventoryMovementEntriesTableTableManager(
          _db, _db.inventoryMovementEntries);
  $$AppSettingEntriesTableTableManager get appSettingEntries =>
      $$AppSettingEntriesTableTableManager(_db, _db.appSettingEntries);
}
