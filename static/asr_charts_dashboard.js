var asrdashboard = new Vue({
    el: '#asrdashboard',
    data: {
      headerMessage: 'ASR Bot Real-Time Dashboard',
      loggedUser: "ameer@twilio.com",
      userAuthenticated: false,
      syncMode: false,
      syncStatus: "Disconnected",
      callList: [],
      Intents: {"Default": 0},
      IntentData: [["MensWare", 25], ["WomensWare", 50], ["TrackOrder", 25], ["PlaceOrder", 15]]
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
          call['ASRConfidence'] = Math.round((parseFloat(data[i].value['Confidence']) * 100.00));
          call['Intent'] = data[i].value['Intent'];
          self.callList.push(call);
        }
        self.callList = _.orderBy(self.callList, ['CallDate'], ['desc']);
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
        call['ASRConfidence'] = Math.round((parseFloat(data.value['Confidence']) * 100.00));
        call['Intent'] = data.value['Intent'];
        self.callList.push(call);
        self.callList = _.orderBy(self.callList, ['CallDate'], ['desc']);
      }    
    },
    computed: {
      reverseCallList: function() {
          // Use lodash provided sort function
          return _.orderBy(this.callList, ['CallDate'], ['desc']);
      },
      totalIVRInteractions: function () {
        return this.callList.length;
      },
      callIntentData: function () {
        var self = this;
        var Intents = {};
        var allIntents = [];
        console.log(self.callList.length)
        if (self.callList.length > 0) {
            for (var i = 0; i < self.callList.length; i++) {
                console.log(self.callList[i]);

                //Intent[self.callList[i]["Intent"]] = Intent[self.callList[i]["Intent"]];
                if ( Intents[self.callList[i]["Intent"]]  >= 0 )
                 {
                  Intents[self.callList[i]["Intent"]] += 1 ;                   
                 }
                else
                {
                  Intents[self.callList[i]["Intent"]] = 0;
                }

            }
            console.log(Intents);

            for ( intent in Intents )
            {
             allIntents.push( [intent, Intents[intent]]);
            }

            //self.Intents = Intent;
        }
        
        console.log("[DEBUG]::" + allIntents);
        return allIntents;
      },
      callIntentTrendsData: function () {
        /*data = [
          {name: 'Workout', data: {'2017-01-01 00:00:00 -0800': 3, '2017-01-02 00:00:00 -0800': 4}},
          {name: 'Call parents', data: {'2017-01-01 00:00:00 -0800': 5, '2017-01-02 00:00:00 -0800': 3}}
        ];
        
        // and
        <line-chart :data="data" />*/
        var self = this;
        var intentTrends = [];
        var intentTrend = {};
        console.log(self.callList.length)
        if (self.callList.length > 0) {
            for (var i = 0; i < self.callList.length; i++) {
                console.log(self.callList[i]);

                //Intent[self.callList[i]["Intent"]] = Intent[self.callList[i]["Intent"]];
                let intentName  = self.callList[i]["Intent"] ; 
                let intentDate = self.callList[i]["CallDate"];
                let intentDateFormatted =  new Date(intentDate.substring(0,10));
                let currIntent = {};


                if ( ! intentTrend[intentName] )
                  {
                    currIntent["name"] = intentName ; 
                    currIntent["data"] = {} ; 
                    currIntent["data"][intentDateFormatted] = 1 ; 
                    intentTrend[intentName] =   currIntent ;   

                  
                  }
                else
                  {
                    currIntent = intentTrend[intentName];
                    if ( ! currIntent["data"][intentDateFormatted] )
                    {
                      currIntent["data"][intentDateFormatted] = 1 ; 
                    }
                    else
                    {
                      currIntent["data"][intentDateFormatted] += 1 ; 
                    }
                   
                    intentTrend[intentName] =   currIntent ;  
                  }
     

            }
            console.log("TREND Data" + JSON.stringify(intentTrend));

            for ( thisIntentTrend in intentTrend )
            {
              intentTrends.push( intentTrend[thisIntentTrend] );
            }

            //self.Intents = Intent;
        }
        
        console.log("[TREND DATA ARRAY]::" + intentTrends);
        return intentTrends;        
 

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