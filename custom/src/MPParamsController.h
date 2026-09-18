#pragma once

#include "FactPanelController.h"

#include <QtCore/QAbstractTableModel>
#include <QtCore/QHash>
#include <QtCore/QMap>
#include <QtCore/QSet>
#include <QtCore/QStringList>
#include <QtGui/QStandardItemModel>

class Fact;
class ParameterManager;

struct MPParameterRow {
    Fact* fact = nullptr;
    QString pendingValue;
    bool favorite = false;
    bool changed = false;
};

class MPParameterTableModel final : public QAbstractTableModel
{
    Q_OBJECT

public:
    enum Column {
        NameColumn = 0,
        ValueColumn,
        DefaultColumn,
        UnitsColumn,
        OptionsColumn,
        DescriptionColumn,
        FavoriteColumn,
        ColumnCount
    };
    Q_ENUM(Column)

    enum Role {
        ChangedRole = Qt::UserRole + 1,
        ReadOnlyRole,
        ParameterNameRole,
        CurrentValueRole,
        PendingValueRole,
        FavoriteRole
    };

    explicit MPParameterTableModel(QObject* parent = nullptr);

    int rowCount(const QModelIndex& parent = QModelIndex()) const override;
    int columnCount(const QModelIndex& parent = QModelIndex()) const override;
    QVariant data(const QModelIndex& index, int role = Qt::DisplayRole) const override;
    QHash<int, QByteArray> roleNames() const override;

    void setRows(QVector<MPParameterRow> rows);
    QString parameterNameAt(int row) const;

private:
    static QString _optionsForFact(Fact* fact);
    QVector<MPParameterRow> _rows;
};

struct MPCompareRow {
    QString name;
    QString vehicleValue;
    QString fileValue;
    bool use = true;
};

class MPCompareTableModel final : public QAbstractTableModel
{
    Q_OBJECT

public:
    enum Column {
        UseColumn = 0,
        NameColumn,
        VehicleColumn,
        FileColumn,
        ColumnCount
    };
    Q_ENUM(Column)

    enum Role {
        UseRole = Qt::UserRole + 1,
        ParameterNameRole,
        VehicleValueRole,
        FileValueRole
    };

    explicit MPCompareTableModel(QObject* parent = nullptr);

    int rowCount(const QModelIndex& parent = QModelIndex()) const override;
    int columnCount(const QModelIndex& parent = QModelIndex()) const override;
    QVariant data(const QModelIndex& index, int role = Qt::DisplayRole) const override;
    QHash<int, QByteArray> roleNames() const override;

    void setRows(QVector<MPCompareRow> rows);
    bool setUse(int row, bool use);
    void setAllUse(bool use);
    const QVector<MPCompareRow>& rows() const { return _rows; }

private:
    QVector<MPCompareRow> _rows;
};

class MPTreeModel final : public QStandardItemModel
{
    Q_OBJECT

public:
    enum Role {
        PrefixRole = Qt::UserRole + 1,
        LeafRole
    };

    explicit MPTreeModel(QObject* parent = nullptr);
    QHash<int, QByteArray> roleNames() const override;
};

class MPParamsController final : public FactPanelController
{
    Q_OBJECT

    Q_PROPERTY(MPParameterTableModel* parameters READ parameters CONSTANT)
    Q_PROPERTY(MPCompareTableModel* compareModel READ compareModel CONSTANT)
    Q_PROPERTY(QAbstractItemModel* treeModel READ treeModel CONSTANT)
    Q_PROPERTY(QString searchText READ searchText WRITE setSearchText NOTIFY searchTextChanged)
    Q_PROPERTY(QString treeFilter READ treeFilter NOTIFY treeFilterChanged)
    Q_PROPERTY(bool showModifiedOnly READ showModifiedOnly WRITE setShowModifiedOnly NOTIFY showModifiedOnlyChanged)
    Q_PROPERTY(int changedCount READ changedCount NOTIFY changedCountChanged)
    Q_PROPERTY(int parameterCount READ parameterCount NOTIFY parameterCountChanged)
    Q_PROPERTY(int compareCount READ compareCount NOTIFY compareCountChanged)
    Q_PROPERTY(QString statusText READ statusText NOTIFY statusTextChanged)
    Q_PROPERTY(double loadProgress READ loadProgress NOTIFY loadProgressChanged)
    Q_PROPERTY(bool parametersReady READ parametersReady NOTIFY parametersReadyChanged)
    Q_PROPERTY(bool pendingWrites READ pendingWrites NOTIFY pendingWritesChanged)

public:
    explicit MPParamsController(QObject* parent = nullptr);

    MPParameterTableModel* parameters() { return &_parameterModel; }
    MPCompareTableModel* compareModel() { return &_compareModel; }
    QAbstractItemModel* treeModel() { return &_treeModel; }

    QString searchText() const { return _searchText; }
    QString treeFilter() const { return _treeFilter; }
    bool showModifiedOnly() const { return _showModifiedOnly; }
    int changedCount() const { return _pendingValues.size(); }
    int parameterCount() const { return _parameterCount; }
    int compareCount() const { return _compareModel.rowCount(); }
    QString statusText() const { return _statusText; }
    double loadProgress() const;
    bool parametersReady() const;
    bool pendingWrites() const;

    void setSearchText(const QString& text);
    void setShowModifiedOnly(bool show);

    Q_INVOKABLE void selectTreeFilter(const QString& prefix, bool exact);
    Q_INVOKABLE void refresh();
    Q_INVOKABLE bool setPendingValue(int row, const QString& value);
    Q_INVOKABLE void toggleFavorite(int row);
    Q_INVOKABLE void discardPending();
    Q_INVOKABLE QString pendingSummary() const;

    Q_INVOKABLE bool loadMpFile(const QString& filename);
    Q_INVOKABLE bool saveMpFile(const QString& filename);
    Q_INVOKABLE bool compareMpFile(const QString& filename);
    Q_INVOKABLE void setCompareUse(int row, bool use);
    Q_INVOKABLE void setAllCompareUse(bool use);
    Q_INVOKABLE void applyCompareSelection();
    Q_INVOKABLE void clearCompare();
    Q_INVOKABLE void writePending();

signals:
    void searchTextChanged();
    void treeFilterChanged();
    void showModifiedOnlyChanged();
    void changedCountChanged();
    void parameterCountChanged();
    void compareCountChanged();
    void statusTextChanged();
    void loadProgressChanged();
    void parametersReadyChanged();
    void pendingWritesChanged();

private:
    static bool _parseMpFile(const QString& filename, QMap<QString, QString>& values, QString& error);
    static bool _valuesEqual(const QString& lhs, const QString& rhs);
    static QString _normaliseNumber(const QString& value, bool* ok = nullptr);
    static bool _skipMpParameter(const QString& name);

    QStringList _allParameterNames() const;
    Fact* _factForName(const QString& name) const;
    void _attachVehicle(Vehicle* vehicle);
    void _rebuildTree();
    void _rebuildTable();
    void _loadFavorites();
    void _saveFavorites();
    void _setStatus(const QString& status);

    ParameterManager* _parameterManager = nullptr;
    MPParameterTableModel _parameterModel;
    MPCompareTableModel _compareModel;
    MPTreeModel _treeModel;

    QString _searchText;
    QString _treeFilter;
    bool _treeFilterExact = false;
    bool _showModifiedOnly = false;
    int _parameterCount = 0;
    QString _statusText;

    QHash<QString, QString> _pendingValues;
    QSet<QString> _favorites;
};
