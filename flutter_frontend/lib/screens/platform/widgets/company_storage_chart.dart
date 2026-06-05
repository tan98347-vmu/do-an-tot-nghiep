// r5/M9 — Bar chart hien thi storage breakdown theo subdir (media/companies/<slug>/*).

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../../../models/company_dashboard.dart';

class CompanyStorageChart extends StatelessWidget {
  final int totalBytes;
  final Map<String, int> bySubdir;
  const CompanyStorageChart({super.key, required this.totalBytes, required this.bySubdir});

  @override
  Widget build(BuildContext context) {
    final entries = bySubdir.entries.where((e) => e.value > 0).toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    final maxVal = entries.isEmpty ? 1.0 : entries.first.value.toDouble();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.storage, size: 20),
                const SizedBox(width: 6),
                const Text('Dung lượng lưu trữ',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                const Spacer(),
                Text('Tổng: ${formatBytes(totalBytes)}',
                    style: const TextStyle(color: Colors.grey)),
              ],
            ),
            const SizedBox(height: 12),
            if (entries.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 24),
                child: Center(child: Text('Chưa có dữ liệu storage.', style: TextStyle(color: Colors.grey))),
              )
            else
              SizedBox(
                height: 220,
                child: BarChart(
                  BarChartData(
                    alignment: BarChartAlignment.spaceAround,
                    maxY: maxVal * 1.1,
                    barTouchData: BarTouchData(
                      enabled: true,
                      touchTooltipData: BarTouchTooltipData(
                        getTooltipItem: (group, _, rod, __) {
                          final name = entries[group.x.toInt()].key;
                          return BarTooltipItem(
                            '$name\n${formatBytes(rod.toY.toInt())}',
                            const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                          );
                        },
                      ),
                    ),
                    titlesData: FlTitlesData(
                      leftTitles: AxisTitles(
                        sideTitles: SideTitles(
                          showTitles: true,
                          reservedSize: 48,
                          getTitlesWidget: (v, _) => Text(
                            formatBytes(v.toInt()),
                            style: const TextStyle(fontSize: 9),
                          ),
                        ),
                      ),
                      rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                      topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                      bottomTitles: AxisTitles(
                        sideTitles: SideTitles(
                          showTitles: true,
                          reservedSize: 36,
                          getTitlesWidget: (v, _) {
                            final i = v.toInt();
                            if (i < 0 || i >= entries.length) return const SizedBox.shrink();
                            return Padding(
                              padding: const EdgeInsets.only(top: 4),
                              child: Text(
                                entries[i].key,
                                style: const TextStyle(fontSize: 10),
                                overflow: TextOverflow.ellipsis,
                              ),
                            );
                          },
                        ),
                      ),
                    ),
                    gridData: const FlGridData(show: true, drawVerticalLine: false),
                    borderData: FlBorderData(show: false),
                    barGroups: [
                      for (var i = 0; i < entries.length; i++)
                        BarChartGroupData(
                          x: i,
                          barRods: [
                            BarChartRodData(
                              toY: entries[i].value.toDouble(),
                              color: Theme.of(context).colorScheme.primary,
                              width: 22,
                              borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
                            ),
                          ],
                        ),
                    ],
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
