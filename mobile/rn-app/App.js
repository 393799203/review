import React from 'react';
import {NavigationContainer} from '@react-navigation/native';
import {createNativeStackNavigator} from '@react-navigation/native-stack';
import {createBottomTabNavigator} from '@react-navigation/bottom-tabs';
import Icon from 'react-native-vector-icons/MaterialIcons';

import LoginScreen from './src/screens/LoginScreen';
import LadderScreen from './src/screens/LadderScreen';
import WatchlistScreen from './src/screens/WatchlistScreen';
import StatisticsScreen from './src/screens/StatisticsScreen';
import NewsScreen from './src/screens/NewsScreen';
import {useAuthStore} from './src/store/authStore';

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

function TabNavigator() {
  return (
    <Tab.Navigator
      screenOptions={({route}) => ({
        tabBarIcon: ({focused, color, size}) => {
          let iconName;

          if (route.name === 'Ladder') {
            iconName = 'trending-up';
          } else if (route.name === 'Watchlist') {
            iconName = 'star';
          } else if (route.name === 'Statistics') {
            iconName = 'bar-chart';
          } else if (route.name === 'News') {
            iconName = 'article';
          }

          return <Icon name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: '#007AFF',
        tabBarInactiveTintColor: 'gray',
        headerShown: true,
      })}>
      <Tab.Screen
        name="Ladder"
        component={LadderScreen}
        options={{title: '梯队分析'}}
      />
      <Tab.Screen
        name="Watchlist"
        component={WatchlistScreen}
        options={{title: '自选股'}}
      />
      <Tab.Screen
        name="Statistics"
        component={StatisticsScreen}
        options={{title: '统计数据'}}
      />
      <Tab.Screen
        name="News"
        component={NewsScreen}
        options={{title: '新闻资讯'}}
      />
    </Tab.Navigator>
  );
}

function App() {
  const isAuthenticated = useAuthStore(state => state.isAuthenticated);

  return (
    <NavigationContainer>
      <Stack.Navigator>
        {!isAuthenticated ? (
          <Stack.Screen
            name="Login"
            component={LoginScreen}
            options={{headerShown: false}}
          />
        ) : (
          <Stack.Screen
            name="Main"
            component={TabNavigator}
            options={{headerShown: false}}
          />
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}

export default App;
