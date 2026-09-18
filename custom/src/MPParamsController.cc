#include "MPParamsController.h"

#include "Fact.h"
#include "ParameterManager.h"
#include "Vehicle.h"
#include "MultiVehicleManager.h"

#include <QtCore/QCollator>
#include <QtCore/QFile>
#include <QtCore/QFileInfo>
#include <QtCore/QLocale>
#include <QtCore/QRegularExpression>
#include <QtCore/QSettings>
#include <QtCore/QTextStream>

#include <algorithm>
#include <cmath>
#include <utility>

namespace {

QString variantToRawString(const QVariant& value)
{
    if (!value.isValid()) {
        return QString();
    }
    bool ok = false;
    const double numeric = value.toDouble(&ok);
    if (ok) {
        return QString::number(numeric, 'g', 17);
    }
    return value.toString();
}

}

MPParameterTableModel::MPParameterTableModel(QObject* parent)
    : QAbstractTableModel(parent)
{
}

int MPParameterTableModel::rowCount(const QModelIndex& parent) const
{
    return parent.isValid() ? 0 : _rows.size();
}

int MPParameterTableModel::columnCount(const QModelIndex& parent) const
{
    return parent.isValid() ? 0 : ColumnCount;
}

QHash<int, QByteArray> MPParameterTableModel::roleNames() const
{
    return {
        {Qt::DisplayRole, "display"},
        {ChangedRole, "changed"},
        {ReadOnlyRole, "readOnly"},
        {ParameterNameRole, "parameterName"},
        {CurrentValueRole, "currentValue"},
        {PendingValueRole, "pendingValue"},
        {FavoriteRole, "favorite"},
    };
}

QString MPParameterTableModel::_optionsForFact(Fact* fact)
{
    if (!fact) {
        return QString();
    }

    QStringList result;
    const QStringList enumStrings = fact->enumStrings();
    const QVariantList enumValues = fact->enumValues();
    const int enumCount = std::min(enumStrings.size(), enumValues.size());
    for (int i = 0; i < enumCount; ++i) {
        result.append(QStringLiteral("%1:%2").arg(enumValues.at(i).toString(), enumStrings.at(i)));
    }

    const QStringList bitmaskStrings = fact->bitmaskStrings();
    const QVariantList bitmaskValues = fact->bitmaskValues();
    const int bitmaskCount = std::min(bitmaskStrings.size(), bitmaskValues.size());
    for (int i = 0; i < bitmaskCount; ++i) {
        result.append(QStringLiteral("%1:%2").arg(bitmaskValues.at(i).toString(), bitmaskStrings.at(i)));
    }

    if (!fact->minIsDefaultForType() || !fact->maxIsDefaultForType()) {
        result.prepend(QStringLiteral("%1 .. %2").arg(variantToRawString(fact->rawMin()), variantToRawString(fact->rawMax())));
    }

    return result.join(QStringLiteral("; "));
}

QVariant MPParameterTableModel::data(const QModelIndex& index, int role) const
{
    if (!index.isValid() || index.row() < 0 || index.row() >= _rows.size()) {
        return {};
    }

    const MPParameterRow& row = _rows.at(index.row());
    Fact* fact = row.fact;
    if (!fact) {
        return {};
    }

    const QString current = fact->rawValueStringFullPrecision();
    const QString pending = row.pendingValue.isEmpty() ? current : row.pendingValue;

    switch (role) {
    case ChangedRole:
        return row.changed;
    case ReadOnlyRole:
        return fact->readOnly();
    case ParameterNameRole:
        return fact->name();
    case CurrentValueRole:
        return current;
    case PendingValueRole:
        return pending;
    case FavoriteRole:
        return row.favorite;
    case Qt::DisplayRole:
        switch (index.column()) {
        case NameColumn:
            return fact->name();
        case ValueColumn:
            return pending;
        case DefaultColumn:
            return fact->defaultValueAvailable() ? variantToRawString(fact->rawDefaultValue()) : QString();
        case UnitsColumn:
            return fact->rawUnits();
        case OptionsColumn:
            return _optionsForFact(fact);
        case DescriptionColumn:
            return fact->shortDescription();
        case FavoriteColumn:
            return row.favorite ? QStringLiteral("★") : QStringLiteral("☆");
        default:
            return {};
        }
    default:
        return {};
    }
}

void MPParameterTableModel::setRows(QVector<MPParameterRow> rows)
{
    beginResetModel();
    _rows = std::move(rows);
    endResetModel();
}

QString MPParameterTableModel::parameterNameAt(int row) const
{
    if (row < 0 || row >= _rows.size() || !_rows.at(row).fact) {
        return {};
    }
    return _rows.at(row).fact->name();
}

MPCompareTableModel::MPCompareTableModel(QObject* parent)
    : QAbstractTableModel(parent)
{
}

int MPCompareTableModel::rowCount(const QModelIndex& parent) const
{
    return parent.isValid() ? 0 : _rows.size();
}

int MPCompareTableModel::columnCount(const QModelIndex& parent) const
{
    return parent.isValid() ? 0 : ColumnCount;
}

QHash<int, QByteArray> MPCompareTableModel::roleNames() const
{
    return {
        {Qt::DisplayRole, "display"},
        {UseRole, "use"},
        {ParameterNameRole, "parameterName"},
        {VehicleValueRole, "vehicleValue"},
        {FileValueRole, "fileValue"},
    };
}

QVariant MPCompareTableModel::data(const QModelIndex& index, int role) const
{
    if (!index.isValid() || index.row() < 0 || index.row() >= _rows.size()) {
        return {};
    }

    const MPCompareRow& row = _rows.at(index.row());
    switch (role) {
    case UseRole:
        return row.use;
    case ParameterNameRole:
        return row.name;
    case VehicleValueRole:
        return row.vehicleValue;
    case FileValueRole:
        return row.fileValue;
    case Qt::DisplayRole:
        switch (index.column()) {
        case UseColumn:
            return row.use;
        case NameColumn:
            return row.name;
        case VehicleColumn:
            return row.vehicleValue;
        case FileColumn:
            return row.fileValue;
        default:
            return {};
        }
    default:
        return {};
    }
}

void MPCompareTableModel::setRows(QVector<MPCompareRow> rows)
{
    beginResetModel();
    _rows = std::move(rows);
    endResetModel();
}

bool MPCompareTableModel::setUse(int row, bool use)
{
    if (row < 0 || row >= _rows.size()) {
        return false;
    }
    if (_rows[row].use == use) {
        return true;
    }
    _rows[row].use = use;
    const QModelIndex left = index(row, 0);
    const QModelIndex right = index(row, ColumnCount - 1);
    emit dataChanged(left, right, {UseRole, Qt::DisplayRole});
    return true;
}

void MPCompareTableModel::setAllUse(bool use)
{
    if (_rows.isEmpty()) {
        return;
    }
    for (MPCompareRow& row : _rows) {
        row.use = use;
    }
    emit dataChanged(index(0, 0), index(_rows.size() - 1, ColumnCount - 1), {UseRole, Qt::DisplayRole});
}

MPTreeModel::MPTreeModel(QObject* parent)
    : QStandardItemModel(parent)
{
}

QHash<int, QByteArray> MPTreeModel::roleNames() const
{
    QHash<int, QByteArray> roles = QStandardItemModel::roleNames();
    roles[PrefixRole] = "prefix";
    roles[LeafRole] = "leaf";
    return roles;
}

MPParamsController::MPParamsController(QObject* parent)
    : FactPanelController(parent)
    , _parameterManager(_vehicle ? _vehicle->parameterManager() : nullptr)
    , _parameterModel(this)
    , _compareModel(this)
    , _treeModel(this)
{
    _loadFavorites();

    MultiVehicleManager* const manager = MultiVehicleManager::instance();
    connect(manager, &MultiVehicleManager::activeVehicleChanged, this, [this](Vehicle* vehicle) {
        _attachVehicle(vehicle);
    });
    _attachVehicle(manager->activeVehicle());
}

void MPParamsController::_attachVehicle(Vehicle* vehicle)
{
    if (_parameterManager) {
        disconnect(_parameterManager, nullptr, this, nullptr);
    }

    _vehicle = vehicle;
    _parameterManager = vehicle ? vehicle->parameterManager() : nullptr;

    if (!_pendingValues.isEmpty()) {
        _pendingValues.clear();
        emit changedCountChanged();
    }
    _compareModel.setRows({});
    emit compareCountChanged();

    if (_parameterManager) {
        connect(_parameterManager, &ParameterManager::loadProgressChanged, this, &MPParamsController::loadProgressChanged);
        connect(_parameterManager, &ParameterManager::parametersReadyChanged, this, [this](bool) {
            _rebuildTree();
            _rebuildTable();
            emit parametersReadyChanged();
        });
        connect(_parameterManager, &ParameterManager::pendingWritesChanged, this, &MPParamsController::pendingWritesChanged);
        connect(_parameterManager, &ParameterManager::factAdded, this, [this](int, Fact*) {
            _rebuildTree();
            _rebuildTable();
        });
    }

    _rebuildTree();
    _rebuildTable();
    emit loadProgressChanged();
    emit parametersReadyChanged();
    emit pendingWritesChanged();
    _setStatus(vehicle
                   ? QStringLiteral("Борт підключено. MP Params готовий до роботи.")
                   : QStringLiteral("Оберіть COM і натисніть Connect або підключіть борт через QGroundControl."));
}

double MPParamsController::loadProgress() const
{
    return _parameterManager ? _parameterManager->loadProgress() : 0.0;
}

bool MPParamsController::parametersReady() const
{
    return _parameterManager && _parameterManager->parametersReady();
}

bool MPParamsController::pendingWrites() const
{
    return _parameterManager && _parameterManager->pendingWrites();
}

void MPParamsController::_setStatus(const QString& status)
{
    if (_statusText == status) {
        return;
    }
    _statusText = status;
    emit statusTextChanged();
}

void MPParamsController::setSearchText(const QString& text)
{
    if (_searchText == text) {
        return;
    }
    _searchText = text;
    emit searchTextChanged();
    _rebuildTable();
}

void MPParamsController::setShowModifiedOnly(bool show)
{
    if (_showModifiedOnly == show) {
        return;
    }
    _showModifiedOnly = show;
    emit showModifiedOnlyChanged();
    _rebuildTable();
}

void MPParamsController::selectTreeFilter(const QString& prefix, bool exact)
{
    if (_treeFilter == prefix && _treeFilterExact == exact) {
        return;
    }
    _treeFilter = prefix;
    _treeFilterExact = exact;
    emit treeFilterChanged();
    _rebuildTable();
}

QStringList MPParamsController::_allParameterNames() const
{
    if (!_parameterManager || !_vehicle) {
        return {};
    }

    QStringList names = _parameterManager->parameterNames(_vehicle->defaultComponentId());
    QCollator collator;
    collator.setNumericMode(true);
    collator.setCaseSensitivity(Qt::CaseInsensitive);
    std::sort(names.begin(), names.end(), [&collator](const QString& a, const QString& b) {
        return collator.compare(a, b) < 0;
    });
    return names;
}

Fact* MPParamsController::_factForName(const QString& name) const
{
    if (!_parameterManager || !_vehicle || !_parameterManager->parameterExists(_vehicle->defaultComponentId(), name)) {
        return nullptr;
    }
    return _parameterManager->getParameter(_vehicle->defaultComponentId(), name);
}

void MPParamsController::_rebuildTree()
{
    _treeModel.clear();

    QStandardItem* all = new QStandardItem(QStringLiteral("All"));
    all->setData(QString(), MPTreeModel::PrefixRole);
    all->setData(false, MPTreeModel::LeafRole);
    _treeModel.invisibleRootItem()->appendRow(all);

    const QStringList names = _allParameterNames();
    QString currentPrefix;
    QStandardItem* currentNode = all;

    for (int i = 0; i < names.size(); ++i) {
        const QString param = names.at(i);

        while (!param.startsWith(currentPrefix) && currentNode && currentNode != all) {
            const QString suffix = currentNode->text().section(QLatin1Char('_'), -1) + QLatin1Char('_');
            if (currentPrefix.endsWith(suffix)) {
                currentPrefix.chop(suffix.size());
            } else {
                currentPrefix.clear();
            }
            currentNode = currentNode->parent();
            if (!currentNode) {
                currentNode = all;
                currentPrefix.clear();
            }
        }

        if (i < names.size() - 1) {
            const QString nextParam = names.at(i + 1);
            QString remainder = param.mid(currentPrefix.size());
            QString nodeToAdd = remainder.section(QLatin1Char('_'), 0, 0) + QLatin1Char('_');

            while (nodeToAdd.size() > 1 &&
                   param.startsWith(currentPrefix + nodeToAdd) &&
                   nextParam.startsWith(currentPrefix + nodeToAdd)) {
                currentPrefix += nodeToAdd;
                QStandardItem* branch = new QStandardItem(currentPrefix.left(currentPrefix.size() - 1));
                branch->setData(currentPrefix, MPTreeModel::PrefixRole);
                branch->setData(false, MPTreeModel::LeafRole);
                currentNode->appendRow(branch);
                currentNode = branch;

                remainder = param.mid(currentPrefix.size());
                nodeToAdd = remainder.section(QLatin1Char('_'), 0, 0) + QLatin1Char('_');
            }
        }

        QStandardItem* leaf = new QStandardItem(param);
        leaf->setData(param, MPTreeModel::PrefixRole);
        leaf->setData(true, MPTreeModel::LeafRole);
        currentNode->appendRow(leaf);
    }
}

void MPParamsController::_rebuildTable()
{
    QVector<MPParameterRow> rows;
    const QStringList names = _allParameterNames();
    _parameterCount = names.size();

    for (const QString& name : names) {
        if (!_treeFilter.isEmpty()) {
            if (_treeFilterExact) {
                if (name != _treeFilter) {
                    continue;
                }
            } else if (!name.startsWith(_treeFilter, Qt::CaseInsensitive)) {
                continue;
            }
        }

        Fact* fact = _factForName(name);
        if (!fact) {
            continue;
        }

        const QString current = fact->rawValueStringFullPrecision();
        const QString pending = _pendingValues.value(name, current);
        const bool changed = !_valuesEqual(current, pending);

        if (_showModifiedOnly && !changed && fact->valueEqualsDefault()) {
            continue;
        }

        if (!_searchText.trimmed().isEmpty()) {
            const QString haystack = name + QLatin1Char(' ') + fact->shortDescription() + QLatin1Char(' ') + fact->longDescription();
            if (!haystack.contains(_searchText.trimmed(), Qt::CaseInsensitive)) {
                continue;
            }
        }

        rows.append({fact, pending, _favorites.contains(name), changed});
    }

    _parameterModel.setRows(std::move(rows));
    emit parameterCountChanged();
}

void MPParamsController::refresh()
{
    if (!_parameterManager) {
        _setStatus(QStringLiteral("Немає підключеного польотника."));
        return;
    }
    _setStatus(QStringLiteral("Зчитування повного списку параметрів..."));
    _parameterManager->refreshAllParameters();
}

QString MPParamsController::_normaliseNumber(const QString& value, bool* ok)
{
    QString normal = value.trimmed();
    normal.replace(QLatin1Char(','), QLatin1Char('.'));
    bool localOk = false;
    const double number = QLocale::c().toDouble(normal, &localOk);
    if (ok) {
        *ok = localOk && std::isfinite(number);
    }
    return localOk && std::isfinite(number) ? QString::number(number, 'g', 17) : QString();
}

bool MPParamsController::_valuesEqual(const QString& lhs, const QString& rhs)
{
    bool okLeft = false;
    bool okRight = false;
    const double left = QLocale::c().toDouble(lhs, &okLeft);
    const double right = QLocale::c().toDouble(rhs, &okRight);
    if (okLeft && okRight && std::isfinite(left) && std::isfinite(right)) {
        const double scale = std::max({1.0, std::abs(left), std::abs(right)});
        return std::abs(left - right) <= 1e-12 * scale;
    }
    return lhs.trimmed() == rhs.trimmed();
}

bool MPParamsController::setPendingValue(int row, const QString& value)
{
    const QString name = _parameterModel.parameterNameAt(row);
    Fact* fact = _factForName(name);
    if (!fact || fact->readOnly()) {
        _setStatus(QStringLiteral("Параметр недоступний для редагування."));
        return false;
    }

    bool ok = false;
    const QString normal = _normaliseNumber(value, &ok);
    if (!ok) {
        _setStatus(QStringLiteral("Некоректне числове значення для %1.").arg(name));
        return false;
    }

    const QString validationError = fact->validate(normal, true);
    if (!validationError.isEmpty()) {
        _setStatus(QStringLiteral("%1: %2").arg(name, validationError));
        return false;
    }

    const int oldCount = changedCount();
    if (_valuesEqual(normal, fact->rawValueStringFullPrecision())) {
        _pendingValues.remove(name);
    } else {
        _pendingValues.insert(name, normal);
    }
    if (changedCount() != oldCount) {
        emit changedCountChanged();
    }
    _rebuildTable();
    return true;
}

void MPParamsController::_loadFavorites()
{
    const QSettings settings;
    const QStringList saved = settings.value(QStringLiteral("MPParams/Favorites")).toStringList();
    _favorites.clear();
    for (const QString& name : saved) {
        _favorites.insert(name);
    }
}

void MPParamsController::_saveFavorites()
{
    QSettings settings;
    QStringList saved;
    saved.reserve(_favorites.size());
    for (const QString& name : std::as_const(_favorites)) {
        saved.append(name);
    }
    saved.sort(Qt::CaseInsensitive);
    settings.setValue(QStringLiteral("MPParams/Favorites"), saved);
}

void MPParamsController::toggleFavorite(int row)
{
    const QString name = _parameterModel.parameterNameAt(row);
    if (name.isEmpty()) {
        return;
    }
    if (_favorites.contains(name)) {
        _favorites.remove(name);
    } else {
        _favorites.insert(name);
    }
    _saveFavorites();
    _rebuildTable();
}

void MPParamsController::discardPending()
{
    if (_pendingValues.isEmpty()) {
        return;
    }
    _pendingValues.clear();
    emit changedCountChanged();
    _rebuildTable();
    _setStatus(QStringLiteral("Незбережені зміни скасовано."));
}

QString MPParamsController::pendingSummary() const
{
    QStringList names = _pendingValues.keys();
    names.sort(Qt::CaseInsensitive);
    QStringList lines;
    const int maxLines = 20;
    for (int i = 0; i < names.size() && i < maxLines; ++i) {
        Fact* fact = _factForName(names.at(i));
        const QString current = fact ? fact->rawValueStringFullPrecision() : QStringLiteral("?");
        lines.append(QStringLiteral("%1: %2 -> %3").arg(names.at(i), current, _pendingValues.value(names.at(i))));
    }
    if (names.size() > maxLines) {
        lines.append(QStringLiteral("... ще %1").arg(names.size() - maxLines));
    }
    return lines.join(QLatin1Char('\n'));
}

bool MPParamsController::_skipMpParameter(const QString& name)
{
    static const QSet<QString> skipped = {
        QStringLiteral("SYSID_SW_MREV"),
        QStringLiteral("WP_TOTAL"),
        QStringLiteral("CMD_TOTAL"),
        QStringLiteral("FENCE_TOTAL"),
        QStringLiteral("SYS_NUM_RESETS"),
        QStringLiteral("ARSPD_OFFSET"),
        QStringLiteral("GND_ABS_PRESS"),
        QStringLiteral("GND_TEMP"),
        QStringLiteral("BARO1_GND_PRESS"),
        QStringLiteral("BARO2_GND_PRESS"),
        QStringLiteral("BARO3_GND_PRESS"),
        QStringLiteral("BARO_GND_TEMP"),
        QStringLiteral("CMD_INDEX"),
        QStringLiteral("LOG_LASTFILE"),
        QStringLiteral("FORMAT_VERSION"),
    };
    return skipped.contains(name);
}

bool MPParamsController::_parseMpFile(const QString& filename, QMap<QString, QString>& values, QString& error)
{
    QFile file(filename);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        error = QStringLiteral("Не вдалося відкрити файл: %1").arg(filename);
        return false;
    }

    QTextStream stream(&file);
    const QRegularExpression separator(QStringLiteral("[,\\s]+"));
    int lineNumber = 0;
    while (!stream.atEnd()) {
        ++lineNumber;
        const QString line = stream.readLine().trimmed();
        if (line.isEmpty() || line.startsWith(QLatin1Char('#'))) {
            continue;
        }

        const QStringList parts = line.split(separator, Qt::SkipEmptyParts);
        if (parts.size() < 2) {
            continue;
        }

        const QString name = parts.at(0).trimmed();
        if (_skipMpParameter(name)) {
            continue;
        }

        bool ok = false;
        const QString value = _normaliseNumber(parts.at(1), &ok);
        if (!ok) {
            error = QStringLiteral("Некоректне число у рядку %1: %2").arg(lineNumber).arg(parts.at(1));
            return false;
        }
        values[name] = value;
    }
    return true;
}

bool MPParamsController::loadMpFile(const QString& filename)
{
    QMap<QString, QString> fileValues;
    QString error;
    if (!_parseMpFile(filename, fileValues, error)) {
        _setStatus(error);
        return false;
    }

    const int oldCount = changedCount();
    int loaded = 0;
    int missing = 0;
    for (auto it = fileValues.cbegin(); it != fileValues.cend(); ++it) {
        Fact* fact = _factForName(it.key());
        if (!fact || fact->readOnly()) {
            ++missing;
            continue;
        }
        if (_valuesEqual(fact->rawValueStringFullPrecision(), it.value())) {
            _pendingValues.remove(it.key());
        } else {
            _pendingValues[it.key()] = it.value();
        }
        ++loaded;
    }

    if (changedCount() != oldCount) {
        emit changedCountChanged();
    }
    _rebuildTable();
    _setStatus(QStringLiteral("MP файл: завантажено %1 параметрів, не знайдено/readonly: %2. Зміни ще не записані на борт.")
                   .arg(loaded)
                   .arg(missing));
    return true;
}

bool MPParamsController::saveMpFile(const QString& filename)
{
    if (!_parameterManager || !_vehicle) {
        _setStatus(QStringLiteral("Немає параметрів для збереження."));
        return false;
    }

    QString output = filename;
    if (QFileInfo(output).suffix().isEmpty()) {
        output += QStringLiteral(".param");
    }

    QFile file(output);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text | QIODevice::Truncate)) {
        _setStatus(QStringLiteral("Не вдалося створити файл: %1").arg(output));
        return false;
    }

    QTextStream stream(&file);
    int saved = 0;
    for (const QString& name : _allParameterNames()) {
        if (_skipMpParameter(name)) {
            continue;
        }
        Fact* fact = _factForName(name);
        if (!fact) {
            continue;
        }
        const QString value = _pendingValues.value(name, fact->rawValueStringFullPrecision());
        stream << name << ',' << value << '\n';
        ++saved;
    }
    file.close();

    _setStatus(QStringLiteral("Збережено %1 параметрів у Mission Planner форматі: %2").arg(saved).arg(output));
    return true;
}

bool MPParamsController::compareMpFile(const QString& filename)
{
    QMap<QString, QString> fileValues;
    QString error;
    if (!_parseMpFile(filename, fileValues, error)) {
        _setStatus(error);
        return false;
    }

    QVector<MPCompareRow> rows;
    for (auto it = fileValues.cbegin(); it != fileValues.cend(); ++it) {
        Fact* fact = _factForName(it.key());
        if (!fact || fact->readOnly()) {
            continue;
        }
        const QString vehicleValue = fact->rawValueStringFullPrecision();
        if (!_valuesEqual(vehicleValue, it.value())) {
            rows.append({it.key(), vehicleValue, it.value(), true});
        }
    }

    _compareModel.setRows(std::move(rows));
    emit compareCountChanged();
    _setStatus(QStringLiteral("Звірка MP файлу: знайдено %1 відмінностей.").arg(compareCount()));
    return true;
}

void MPParamsController::setCompareUse(int row, bool use)
{
    _compareModel.setUse(row, use);
}

void MPParamsController::setAllCompareUse(bool use)
{
    _compareModel.setAllUse(use);
}

void MPParamsController::applyCompareSelection()
{
    const int oldCount = changedCount();
    int applied = 0;
    for (const MPCompareRow& row : _compareModel.rows()) {
        if (!row.use) {
            continue;
        }
        Fact* fact = _factForName(row.name);
        if (!fact || fact->readOnly()) {
            continue;
        }
        _pendingValues[row.name] = row.fileValue;
        ++applied;
    }

    if (changedCount() != oldCount) {
        emit changedCountChanged();
    }
    _rebuildTable();
    _setStatus(QStringLiteral("До черги змін додано %1 параметрів зі звірки. Натисніть Write Params для запису.").arg(applied));
}

void MPParamsController::clearCompare()
{
    _compareModel.setRows({});
    emit compareCountChanged();
}

void MPParamsController::writePending()
{
    if (!_parameterManager || !_vehicle) {
        _setStatus(QStringLiteral("Немає підключеного польотника."));
        return;
    }
    if (_pendingValues.isEmpty()) {
        _setStatus(QStringLiteral("Немає змінених параметрів для запису."));
        return;
    }

    QStringList names = _pendingValues.keys();
    names.sort(Qt::CaseInsensitive);

    int sent = 0;
    int skipped = 0;
    for (const QString& name : names) {
        Fact* fact = _factForName(name);
        if (!fact || fact->readOnly()) {
            ++skipped;
            continue;
        }

        const QString value = _pendingValues.value(name);
        const QString validationError = fact->validate(value, true);
        if (!validationError.isEmpty()) {
            ++skipped;
            continue;
        }

        fact->setRawValue(value);
        ++sent;
    }

    _pendingValues.clear();
    emit changedCountChanged();
    _rebuildTable();
    _setStatus(QStringLiteral("Відправлено на запис %1 параметрів; пропущено %2.").arg(sent).arg(skipped));
}
