var asrdashboard = new Vue({
    el: '#asrdashboard',
    data: {
      headerMessage: 'ASR Bot Real-Time Dashboard',
      loggedUser: "mnspoc@gmail.com",
      userAuthenticated: false,
      syncMode: false,
      syncStatus: "Disconnected",
      callList: [],
    },
    methods: {
      syncRetrieveCallMap: function(data) {
        var self = this;
        var call = {};
        //console.log(data[0]);
        for (let i = 0 ; i < data.length ; i++ ) {
          call = {};
          call['CallSid'] = data[i].value['CallSid'];
          call['CallDate'] = data[i].value['CallDate'];;
          call['From'] = data[i].value['From'];
          call['CallStatus'] = data[i].value['CallStatus'];
          call['SpeechResult'] = data[i].value['SpeechResult'];
          call['ASRConfidence'] = data[i].value['Confidence'];
          call['Intent'] = data[i].value['Intent'];
          self.callList.push(call);
        }
      },
      syncCallMap: function(data) {
        var self = this;
        var call = {};
        //console.log(data);
        call = {};
        call['CallSid'] = data.value['CallSid'];
        call['CallDate'] = data.value['CallDate'];;
        call['From'] = data.value['From'];
        call['CallStatus'] = data.value['CallStatus'];
        call['SpeechResult'] = data.value['SpeechResult'];
        call['ASRConfidence'] = data.value['Confidence'];
        call['Intent'] = data.value['Intent'];
        self.callList.push(call);
        self.callList = _.orderBy(self.callList, ['CallDate'], ['desc']);
      }    
    },
    computed: {
      reverseCallList: function() {
          // Use lodash provided sort function
          return _.orderBy(this.callList, ['CallDate'], ['desc']);
      }
    },  
  })
  // Twilio Sync setup
  //Our interface to the Sync service
  var syncClient;
  //We're going to use a Sync Map for this demo
  var syncMapName;
  var userid = asrdashboard.$data.loggedUser;
  var ts = Math.round((new Date()).getTime() / 1000);
  tokenUserid = userid + ts;
  asrdashboard.$data.syncEndpoint = tokenUserid;
  $.getJSON('/token' + '?identity=' + tokenUserid, function (tokenResponse) {
    //Initialize the Sync client
    syncClient = new Twilio.Sync.Client(tokenResponse.token, { logLevel: 'info' });
    asrdashboard.$data.syncStatus = userid + ' Connected';
    //Get current Map and then subsribe to add and update events
    syncMapName = 'ASRBotEvents';
    syncClient.map(syncMapName).then(function(map) {
      map.getItems().then(function(page) {
        //console.log('show first item', page.items[0].key, page.items[0].value);
        asrdashboard.syncRetrieveCallMap(page.items);
      });
    });
    syncClient.map(syncMapName).then(function (map) {
      //Note that there are two separate events for map item adds and map item updates:
      map.on('itemAdded', function(item) {
        // console.log('key', item.key);
        console.log('New ASRBotEvents Data:', item);
        asrdashboard.syncCallMap(item);
      });
      map.on('itemUpdated', function(item) {
        // console.log('key', item.key);
        console.log('Updated ASRBotEvents Data:', item);
        //asrdashboard.syncCallMap(item);
      });
    });
  });
