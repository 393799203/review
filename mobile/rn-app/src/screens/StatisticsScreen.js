import React, {useState, useEffect} from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import {stockApi} from '../services/api';
import dayjs from 'dayjs';

export default function StatisticsScreen() {
  const [statistics, setStatistics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadStatistics();
  }, []);

  const loadStatistics = async () => {
    setLoading(true);
    try {
      const response = await stockApi.getLatestDate();
      if (response.data.success && response.data.latest_date) {
        const statsResponse = await stockApi.getStatistics(
          response.data.latest_date,
        );
        if (statsResponse.data.success) {
          setStatistics(statsResponse.data.data);
        }
      }
    } catch (error) {
      console.error('加载统计数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadStatistics();
    setRefreshing(false);
  };

  if (loading && !refreshing) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
      </View>
    );
  }

  if (!statistics) {
    return (
      <View style={styles.emptyContainer}>
        <Text style={styles.emptyText}>暂无统计数据</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>市场概况</Text>
        <View style={styles.statRow}>
          <Text style={styles.statLabel}>涨停数量</Text>
          <Text style={[styles.statValue, {color: '#FF4D4F'}]}>
            {statistics.limit_up_count || 0}
          </Text>
        </View>
        <View style={styles.statRow}>
          <Text style={styles.statLabel}>跌停数量</Text>
          <Text style={[styles.statValue, {color: '#52C41A'}]}>
            {statistics.limit_down_count || 0}
          </Text>
        </View>
        <View style={styles.statRow}>
          <Text style={styles.statLabel}>上涨家数</Text>
          <Text style={[styles.statValue, {color: '#FF4D4F'}]}>
            {statistics.up_count || 0}
          </Text>
        </View>
        <View style={styles.statRow}>
          <Text style={styles.statLabel}>下跌家数</Text>
          <Text style={[styles.statValue, {color: '#52C41A'}]}>
            {statistics.down_count || 0}
          </Text>
        </View>
      </View>

      {statistics.block_stats && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>板块统计</Text>
          {Object.entries(statistics.block_stats).map(([block, count]) => (
            <View key={block} style={styles.statRow}>
              <Text style={styles.statLabel}>{block}</Text>
              <Text style={styles.statValue}>{count}</Text>
            </View>
          ))}
        </View>
      )}

      <View style={styles.card}>
        <Text style={styles.cardTitle}>数据日期</Text>
        <Text style={styles.dateText}>
          {dayjs(statistics.date).format('YYYY年MM月DD日')}
        </Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 16,
    color: '#999',
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 8,
    margin: 10,
    marginBottom: 10,
    padding: 15,
    shadowColor: '#000',
    shadowOffset: {width: 0, height: 1},
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 15,
  },
  statRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  statLabel: {
    fontSize: 16,
    color: '#666',
  },
  statValue: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
  },
  dateText: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
  },
});
