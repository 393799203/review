import React, {useState, useEffect} from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
  ActivityIndicator,
  Alert,
} from 'react-native';
import {stockApi} from '../services/api';

export default function WatchlistScreen() {
  const [watchlist, setWatchlist] = useState([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadWatchlist();
  }, []);

  const loadWatchlist = async () => {
    setLoading(true);
    try {
      const response = await stockApi.getWatchlist();
      if (response.data.success) {
        setWatchlist(response.data.data || []);
      }
    } catch (error) {
      console.error('加载自选股失败:', error);
      Alert.alert('错误', '加载自选股失败');
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    try {
      await stockApi.updateWatchlistPrices();
      await loadWatchlist();
    } catch (error) {
      console.error('更新失败:', error);
    } finally {
      setRefreshing(false);
    }
  };

  const handleDelete = (stockCode, stockName) => {
    Alert.alert(
      '确认删除',
      `确定要删除 ${stockName} 吗？`,
      [
        {text: '取消', style: 'cancel'},
        {
          text: '删除',
          style: 'destructive',
          onPress: async () => {
            try {
              const response = await stockApi.sellStock({
                stock_code: stockCode,
                sell_quantity: 0,
              });
              if (response.data.success) {
                Alert.alert('成功', '删除成功');
                loadWatchlist();
              } else {
                Alert.alert('错误', response.data.error || '删除失败');
              }
            } catch (error) {
              Alert.alert('错误', '删除失败');
            }
          },
        },
      ],
    );
  };

  const renderStock = ({item}) => (
    <TouchableOpacity
      style={styles.stockItem}
      onLongPress={() => handleDelete(item.stock_code, item.stock_name)}>
      <View style={styles.stockInfo}>
        <Text style={styles.stockName}>{item.stock_name}</Text>
        <Text style={styles.stockCode}>{item.stock_code}</Text>
      </View>
      <View style={styles.stockDetails}>
        <View style={styles.priceRow}>
          <Text style={styles.label}>当前价:</Text>
          <Text
            style={[
              styles.priceValue,
              {color: item.change_rate >= 0 ? '#FF4D4F' : '#52C41A'},
            ]}>
            {item.current_price?.toFixed(2)}
          </Text>
        </View>
        <View style={styles.priceRow}>
          <Text style={styles.label}>涨跌幅:</Text>
          <Text
            style={[
              styles.changeValue,
              {color: item.change_rate >= 0 ? '#FF4D4F' : '#52C41A'},
            ]}>
            {item.change_rate >= 0 ? '+' : ''}
            {(item.change_rate * 100).toFixed(2)}%
          </Text>
        </View>
        {item.buy_price && (
          <View style={styles.priceRow}>
            <Text style={styles.label}>买入价:</Text>
            <Text style={styles.priceValue}>{item.buy_price?.toFixed(2)}</Text>
          </View>
        )}
        {item.buy_quantity && (
          <View style={styles.priceRow}>
            <Text style={styles.label}>持仓:</Text>
            <Text style={styles.priceValue}>{item.buy_quantity}股</Text>
          </View>
        )}
      </View>
    </TouchableOpacity>
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
      <FlatList
        data={watchlist}
        keyExtractor={item => item.stock_code}
        renderItem={renderStock}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        contentContainerStyle={styles.listContainer}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>暂无自选股</Text>
          </View>
        }
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
  listContainer: {
    padding: 10,
  },
  stockItem: {
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
  stockInfo: {
    marginBottom: 10,
    paddingBottom: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E5E5',
  },
  stockName: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  stockCode: {
    fontSize: 12,
    color: '#999',
    marginTop: 2,
  },
  stockDetails: {
    marginTop: 5,
  },
  priceRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 5,
  },
  label: {
    fontSize: 14,
    color: '#666',
  },
  priceValue: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
  },
  changeValue: {
    fontSize: 14,
    fontWeight: '600',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 100,
  },
  emptyText: {
    fontSize: 16,
    color: '#999',
  },
});
