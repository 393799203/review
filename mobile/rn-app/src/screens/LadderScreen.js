import React, {useState, useEffect} from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
  ActivityIndicator,
} from 'react-native';
import {useGlobalStore} from '../store/globalStore';
import {stockApi} from '../services/api';
import dayjs from 'dayjs';

export default function LadderScreen() {
  const [ladderData, setLadderData] = useState([]);
  const [dates, setDates] = useState([]);
  const [selectedDate, setSelectedDate] = useState('');
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadDates();
  }, []);

  useEffect(() => {
    if (selectedDate) {
      loadLadderData(selectedDate);
    }
  }, [selectedDate]);

  const loadDates = async () => {
    try {
      const response = await stockApi.getAvailableDates();
      if (response.data.success) {
        setDates(response.data.dates || []);
        if (response.data.dates && response.data.dates.length > 0) {
          setSelectedDate(response.data.dates[0]);
        }
      }
    } catch (error) {
      console.error('加载日期失败:', error);
    }
  };

  const loadLadderData = async date => {
    setLoading(true);
    try {
      const response = await stockApi.getLadderByDate(date);
      if (response.data.success) {
        setLadderData(response.data.data || []);
      }
    } catch (error) {
      console.error('加载梯队数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadLadderData(selectedDate);
    setRefreshing(false);
  };

  const renderBlock = ({item}) => (
    <View style={styles.blockContainer}>
      <View style={styles.blockHeader}>
        <Text style={styles.blockTitle}>{item.block_name}</Text>
        <Text style={styles.blockCount}>{item.stocks?.length || 0}只股票</Text>
      </View>
      <FlatList
        data={item.stocks || []}
        keyExtractor={stock => stock.stock_code}
        renderItem={({item: stock}) => (
          <View style={styles.stockItem}>
            <View style={styles.stockInfo}>
              <Text style={styles.stockName}>{stock.stock_name}</Text>
              <Text style={styles.stockCode}>{stock.stock_code}</Text>
            </View>
            <View style={styles.stockPrice}>
              <Text
                style={[
                  styles.priceText,
                  {color: stock.change_rate >= 0 ? '#FF4D4F' : '#52C41A'},
                ]}>
                {stock.current_price?.toFixed(2)}
              </Text>
              <Text
                style={[
                  styles.changeText,
                  {color: stock.change_rate >= 0 ? '#FF4D4F' : '#52C41A'},
                ]}>
                {stock.change_rate >= 0 ? '+' : ''}
                {(stock.change_rate * 100).toFixed(2)}%
              </Text>
            </View>
          </View>
        )}
      />
    </View>
  );

  if (loading && !refreshing) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.dateSelector}>
        <FlatList
          horizontal
          data={dates.slice(0, 10)}
          keyExtractor={date => date}
          renderItem={({item: date}) => (
            <TouchableOpacity
              style={[
                styles.dateItem,
                selectedDate === date && styles.dateItemActive,
              ]}
              onPress={() => setSelectedDate(date)}>
              <Text
                style={[
                  styles.dateText,
                  selectedDate === date && styles.dateTextActive,
                ]}>
                {dayjs(date).format('MM-DD')}
              </Text>
            </TouchableOpacity>
          )}
          showsHorizontalScrollIndicator={false}
        />
      </View>

      <FlatList
        data={ladderData}
        keyExtractor={item => item.block_name}
        renderItem={renderBlock}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        contentContainerStyle={styles.listContainer}
      />
    </View>
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
  dateSelector: {
    backgroundColor: '#FFFFFF',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5E5',
  },
  dateItem: {
    paddingHorizontal: 15,
    paddingVertical: 8,
    marginHorizontal: 5,
    borderRadius: 15,
    backgroundColor: '#F0F0F0',
  },
  dateItemActive: {
    backgroundColor: '#007AFF',
  },
  dateText: {
    fontSize: 14,
    color: '#666',
  },
  dateTextActive: {
    color: '#FFFFFF',
    fontWeight: '600',
  },
  listContainer: {
    padding: 10,
  },
  blockContainer: {
    backgroundColor: '#FFFFFF',
    borderRadius: 8,
    marginBottom: 10,
    padding: 15,
    shadowColor: '#000',
    shadowOffset: {width: 0, height: 1},
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  blockHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
    paddingBottom: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5E5',
  },
  blockTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  blockCount: {
    fontSize: 14,
    color: '#999',
  },
  stockItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  stockInfo: {
    flex: 1,
  },
  stockName: {
    fontSize: 16,
    fontWeight: '500',
    color: '#333',
  },
  stockCode: {
    fontSize: 12,
    color: '#999',
    marginTop: 2,
  },
  stockPrice: {
    alignItems: 'flex-end',
  },
  priceText: {
    fontSize: 16,
    fontWeight: '600',
  },
  changeText: {
    fontSize: 12,
    marginTop: 2,
  },
});
