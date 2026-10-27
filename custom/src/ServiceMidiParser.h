#pragma once

#include <QtCore/QByteArray>
#include <QtCore/QFile>
#include <QtCore/QUrl>
#include <QtCore/QVector>
#include <QtCore/QtGlobal>
#include <algorithm>

namespace ServiceMidiParser {
struct Note { quint32 tick; quint32 end; quint8 pitch; };
struct Tempo { quint32 tick; quint32 us; };
inline quint16 be16(const QByteArray &b, int i) {
    return (quint8(b[i]) << 8) | quint8(b[i + 1]);
}
inline quint32 be32(const QByteArray &b, int i) {
    return (quint32(quint8(b[i])) << 24) | (quint32(quint8(b[i+1])) << 16)
         | (quint32(quint8(b[i+2])) << 8) | quint8(b[i+3]);
}
inline bool vlq(const QByteArray &b, int &i, int end, quint32 &value) {
    value = 0;
    for (int j = 0; j < 4; ++j) {
        if (i >= end) return false;
        const quint8 c = quint8(b[i++]);
        value = (value << 7) | (c & 0x7f);
        if (!(c & 0x80)) return true;
    }
    return false;
}
inline bool parse(const QUrl &url, QByteArray &packed, double &durationSeconds) {
    const QString local = url.isLocalFile() ? url.toLocalFile() : url.toString();
    QFile file(local);
    if (!file.open(QIODevice::ReadOnly) || file.size() > 4 * 1024 * 1024) return false;
    const QByteArray b = file.readAll();
    if (b.size() < 14 || b.left(4) != "MThd") return false;
    const quint32 headerSize = be32(b, 4);
    if (headerSize < 6 || headerSize > quint32(b.size()-8)) return false;
    const quint16 format = be16(b, 8);
    const quint16 tracks = be16(b, 10);
    const quint16 division = be16(b, 12);
    if (format > 1 || tracks == 0 || tracks > 128 || division == 0 || (division & 0x8000)) return false;
    QVector<Note> notes;
    QVector<Tempo> tempos{{0, 500000}};
    int pos = 8 + int(headerSize);
    for (int tr = 0; tr < tracks; ++tr) {
        if (pos + 8 > b.size() || b.mid(pos, 4) != "MTrk") return false;
        const quint32 length = be32(b, pos+4);
        pos += 8;
        if (length > quint32(b.size()-pos)) return false;
        const int end = pos + int(length);
        quint32 tick = 0;
        quint8 running = 0;
        int active[16][128];
        for (auto &channel : active) for (int &index : channel) index = -1;
        while (pos < end) {
            quint32 delta = 0;
            if (!vlq(b, pos, end, delta) || tick > 0xFFFFFFFFu-delta) return false;
            tick += delta;
            if (pos >= end) return false;
            quint8 status = quint8(b[pos]);
            if (status & 0x80) { ++pos; if (status < 0xF0) running = status; }
            else if (running) status = running;
            else return false;
            if (status == 0xFF) {
                if (pos >= end) return false;
                quint8 meta = quint8(b[pos++]);
                quint32 n = 0;
                if (!vlq(b, pos, end, n) || n > quint32(end-pos)) return false;
                if (meta == 0x51 && n == 3) {
                    quint32 us = (quint32(quint8(b[pos])) << 16) |
                        (quint32(quint8(b[pos+1])) << 8) | quint8(b[pos+2]);
                    if (us) tempos.append({tick, us});
                }
                pos += int(n);
            } else if (status == 0xF0 || status == 0xF7) {
                quint32 n = 0;
                if (!vlq(b, pos, end, n) || n > quint32(end-pos)) return false;
                pos += int(n);
                running = 0;
            } else if ((status & 0xF0) >= 0x80 && (status & 0xF0) <= 0xE0) {
                const int kind = status & 0xF0;
                const int channel = status & 0x0F;
                const int count = (kind == 0xC0 || kind == 0xD0) ? 1 : 2;
                if (pos + count > end) return false;
                const quint8 pitch = quint8(b[pos++]);
                const quint8 velocity = count == 2 ? quint8(b[pos++]) : 0;
                if (kind == 0x90 && velocity != 0 && pitch < 128) {
                    active[channel][pitch] = notes.size();
                    notes.append({tick, tick + division / 4, pitch});
                } else if ((kind == 0x80 || (kind == 0x90 && velocity == 0)) && pitch < 128) {
                    int index = active[channel][pitch];
                    if (index >= 0 && index < notes.size()) notes[index].end = qMax(tick, notes[index].tick+1);
                    active[channel][pitch] = -1;
                }
            } else return false;
        }
    }
    if (notes.isEmpty()) return false;
    std::stable_sort(tempos.begin(), tempos.end(), [](const Tempo &a, const Tempo &b) { return a.tick < b.tick; });
    std::stable_sort(notes.begin(), notes.end(), [](const Note &a, const Note &b) { return a.tick < b.tick; });
    auto toMs = [&](quint32 tick) -> double {
        quint32 lastTick = 0, us = 500000;
        double total = 0;
        for (const auto &tempo : tempos) {
            if (tempo.tick > tick) break;
            if (tempo.tick > lastTick) total += (tempo.tick - lastTick) * double(us) / division / 1000.0;
            lastTick = tempo.tick;
            us = tempo.us;
        }
        return total + (tick - lastTick) * double(us) / division / 1000.0;
    };
    packed.clear();
    double lastStart = -1;
    double finalMs = 0;
    // The buzzer is monophonic: choose a single note per simultaneous onset.
    for (const auto &note : notes) {
        const double ms = toMs(note.tick);
        if (ms > 175000) break; // packed score has a 16-bit time index
        if (ms - lastStart < 16.0) continue;
        lastStart = ms;
        const double endMs = toMs(note.end);
        finalMs = qMax(finalMs, endMs);
        const int t = qBound(0, int(ms / (260870.0 / 96000.0)), 65535);
        const int d = qBound(1, int((endMs - ms) / (260870.0 / 96000.0)), 65535);
        packed.append(char(t & 255)); packed.append(char((t >> 8) & 255));
        packed.append(char(d & 255)); packed.append(char((d >> 8) & 255));
        packed.append(char(note.pitch));
    }
    durationSeconds = qMin(175.0, (finalMs + 50.0) / 1000.0);
    return !packed.isEmpty();
}
}
