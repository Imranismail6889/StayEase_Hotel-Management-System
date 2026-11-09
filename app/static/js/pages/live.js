/* API-backed dashboard data and admin controls. */
async function loadDashboardData() {
  if (!state.user) return;
  try {
    if (state.user.role === "admin") {
      const values = await Promise.all([api.getAdminStats(), api.getAdminBookings(), api.getAdminCustomers(), api.getTodayBoard(), api.getActivity(), api.getSettings(), api.getPromos()]);
      state.adminStats = values[0];
      bookings = values[1].items || [];
      state.customers = values[2].items || [];
      state.todayBoard = values[3];
      state.activityItems = values[4];
      state.settings = values[5];
      state.promos = values[6];
    } else {
      const values = await Promise.all([api.getBookings(), api.getFavorites(), api.getMyReviews(), api.getLoyaltyHistory()]);
      bookings = values[0];
      state.favorites = new Set(values[1].map(function(room) { return room.id; }));
      state.myReviews = values[2].items || [];
      state.loyaltyHistory = values[3].items || [];
    }
    const inbox = await api.getNotifications();
    state.notificationsList = inbox.items || [];
    render();
  } catch (error) { toast(error.message, "error"); }
}

function navigate(page, id) {
  if (page === "dashboard" && !state.user) { state.page = "login"; state.modal = null; render(); return; }
  state.page = page; state.mobile = false; state.modal = null;
  if (id) state.roomId = Number(id);
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (page === "rooms" && (!state.roomsLoaded || state.forceRoomReload)) {
    state.roomsLoading = true; render();
    api.getRooms(state.searchDates ? { check_in: state.searchDates.cin, check_out: state.searchDates.cout } : {}).then(function(items) {
      rooms.splice(0, rooms.length, ...items); state.roomsLoaded = true; state.forceRoomReload = false; state.roomsLoading = false; render();
    }).catch(function(error) { state.roomsLoading = false; toast(error.message, "error"); render(); });
    return;
  }
  render();
  if (page === "dashboard") loadDashboardData();
  if (page === "details" && id) {
    if (state.user) updateDetailQuote();
    Promise.all([api.getRoomReviews(id), api.getAvailability(id, new Date().toISOString().slice(0, 8) + "01", new Date(new Date().getFullYear(), new Date().getMonth() + 1, 1).toISOString().slice(0, 10))]).then(function(results) {
      state.roomReviews = results[0].items || [];
      const days = [];
      (results[1].booked_ranges || []).forEach(function(range) {
        let day = new Date(range.from + "T00:00:00"), end = new Date(range.to + "T00:00:00");
        while (day < end) { if (day.getMonth() === new Date().getMonth()) days.push(day.getDate()); day.setDate(day.getDate() + 1); }
      });
      const room = getRoom(id); if (room) room.booked = days;
      render();
    }).catch(function(error) { toast(error.message, "error"); });
  }
}

function adminOverview() {
  const stats = state.adminStats || {}, status = stats.room_status_counts || {}, board = state.todayBoard || {};
  const activities = state.activityItems || [];
  const rows = bookings.slice(0, 5).map(function(item) {
    return '<div class="booking-row"><div><strong>' + esc(item.guest) + '</strong><small>' + esc(item.id) + '</small></div><div>' + esc(item.room) + '</div><div>' + statusTag(item.status) + '</div></div>';
  }).join("");
  const feed = activities.slice(0, 8).map(function(item) {
    return '<div class="activity-item"><i></i><span>' + esc(item.guest) + ' · ' + esc(item.booking_ref) + ' · ' + esc(item.status.replaceAll("_", " ")) + '</span></div>';
  }).join("");
  return '<div class="dash-stats admin-stats">' +
    [['Total revenue', money(stats.total_revenue || 0)], ['Occupancy', Number(stats.occupancy_rate || 0) + "%"], ['Active bookings', Number(stats.active_bookings || 0)], ['Customers', Number(stats.total_customers || 0)]].map(function(item) { return '<div class="dash-stat"><span>' + item[0] + '</span><strong>' + item[1] + '</strong></div>'; }).join("") +
    '</div><div class="admin-charts"><div class="dash-card"><div class="dash-card-head"><h3>Revenue overview</h3><div class="view-switch"><button class="active" data-action="chart-mode" data-mode="bar">Bar</button><button data-action="chart-mode" data-mode="line">Line</button></div></div>' + revenueChart() + '</div>' +
    '<div class="dash-card"><div class="dash-card-head"><h3>Room status</h3><span class="tag gold">Live</span></div><div class="today-grid"><div class="today-box"><strong>' + (status.available || 0) + '</strong><small>Available</small></div><div class="today-box"><strong>' + (status.occupied || 0) + '</strong><small>Occupied</small></div><div class="today-box"><strong>' + (status.maintenance || 0) + '</strong><small>Maintenance</small></div></div></div></div>' +
    '<div class="admin-charts"><div class="dash-card"><div class="dash-card-head"><h3>Today board</h3><span class="tag gold">' + new Date().toLocaleDateString() + '</span></div><div class="today-grid"><div class="today-box"><strong>' + (board.arrival_count || 0) + '</strong><small>Arrivals</small></div><div class="today-box"><strong>' + (board.departure_count || 0) + '</strong><small>Departures</small></div><div class="today-box"><strong>' + (board.in_house_count || 0) + '</strong><small>In-house</small></div></div><div class="dash-card-head" style="margin-top:24px"><h3>Recent reservations</h3><button class="btn btn-ghost btn-sm" data-action="admin-tab" data-tab="Bookings">See all →</button></div>' + (rows || '<p class="muted">No reservations yet.</p>') + '</div><div class="dash-card"><div class="dash-card-head"><h3>Recent activity</h3></div><div class="activity">' + (feed || '<p class="muted">No recent activity.</p>') + '</div></div></div>';
}

function adminRooms() {
  const list = rooms.filter(function(room) { return room.name.toLowerCase().includes((state.roomSearch || "").toLowerCase()); });
  return '<div class="dash-card"><div class="dash-card-head"><h3>Room control</h3><button class="btn btn-primary btn-sm" data-action="add-room">＋ Add a room</button></div><div class="field" style="max-width:290px;margin-bottom:15px"><input placeholder="Search rooms…" id="room-search" value="' + esc(state.roomSearch || "") + '"></div><div class="table-scroll"><table class="data-table"><thead><tr><th>Room</th><th>Type</th><th>Rate</th><th>Capacity</th><th>Status</th><th>Actions</th></tr></thead><tbody>' +
    list.map(function(room) { return '<tr><td><strong>' + esc(room.room_number) + ' · ' + esc(room.name) + '</strong></td><td>' + esc(room.type) + '</td><td>' + money(room.price) + '</td><td>' + room.capacity + '</td><td><select class="control" data-room-status="' + room.id + '">' + ['Available','Occupied','Maintenance'].map(function(status) { return '<option ' + (room.status === status ? 'selected' : '') + '>' + status + '</option>'; }).join("") + '</select></td><td><button class="btn btn-outline btn-sm" data-action="edit-room" data-id="' + room.id + '">Edit</button> <button class="btn btn-danger btn-sm" data-action="delete-room" data-id="' + room.id + '">×</button></td></tr>'; }).join("") +
    '</tbody></table></div></div>';
}

function adminBookings() {
  const list = bookings.filter(function(item) {
    const matches = [item.id, item.guest, item.room].join(" ").toLowerCase().includes((state.bookingSearch || "").toLowerCase());
    return matches && ((state.bookingsFilter || "All") === "All" || item.status === state.bookingsFilter);
  });
  return '<div class="dash-card"><div class="dash-card-head"><h3>Reservations</h3><button class="btn btn-outline btn-sm" data-action="export-csv">↓ Export CSV</button></div><div class="filter-panel" style="margin-bottom:15px;padding:10px"><div class="field"><label>Search guest or ID</label><input id="booking-search" placeholder="Search…" value="' + esc(state.bookingSearch || "") + '"></div><div class="field"><label>Status</label><select id="admin-booking-status">' + ['All','Confirmed','Checked In','Completed','Cancelled'].map(function(status) { return '<option ' + ((state.bookingsFilter || "All") === status ? 'selected' : '') + '>' + status + '</option>'; }).join("") + '</select></div></div><div class="table-scroll"><table class="data-table"><thead><tr><th>Reservation</th><th>Guest</th><th>Room</th><th>Stay dates</th><th>Total</th><th>Status</th><th>Action</th></tr></thead><tbody>' +
    list.map(function(item) { let actions = '—'; if (item.status === 'Confirmed') actions = '<button class="btn btn-outline btn-sm" data-action="approve-booking" data-id="' + esc(item.id) + '">Check in</button> <button class="btn btn-danger btn-sm" data-action="admin-cancel" data-id="' + esc(item.id) + '">Cancel</button>'; else if (item.status === 'Checked In') actions = '<button class="btn btn-outline btn-sm" data-action="checkout-booking" data-id="' + esc(item.id) + '">Check out</button>'; return '<tr><td><strong>' + esc(item.id) + '</strong></td><td>' + esc(item.guest) + '</td><td>' + esc(item.room) + '</td><td>' + esc(item.dates) + '</td><td>' + money(item.total) + '</td><td>' + statusTag(item.status) + '</td><td>' + actions + '</td></tr>'; }).join("") +
    '</tbody></table></div>' + (list.length ? '' : '<div class="empty-state"><h3 class="serif">No reservations match.</h3><p>Try another search or status.</p></div>') + '</div>';
}

function adminCustomers() {
  const list = (state.customers || []).filter(function(user) { return [user.name,user.email].join(" ").toLowerCase().includes((state.customerSearch || "").toLowerCase()); });
  return '<div class="dash-card"><div class="dash-card-head"><h3>Guests</h3><span class="tag gold">' + list.length + ' members</span></div><div class="field" style="max-width:310px;margin-bottom:15px"><input id="customer-search" placeholder="Search guests…" value="' + esc(state.customerSearch || "") + '"></div><div class="table-scroll"><table class="data-table"><thead><tr><th>Guest</th><th>Email</th><th>Visits</th><th>Total spent</th><th>Status</th><th></th></tr></thead><tbody>' +
    list.map(function(user) { return '<tr><td><strong>' + esc(user.name) + '</strong></td><td>' + esc(user.email) + '</td><td>' + (user.bookings_count || 0) + '</td><td>' + money(user.total_spent || 0) + '</td><td>' + (user.is_active ? '<span class="tag green">Active</span>' : '<span class="tag red">Inactive</span>') + '</td><td><button class="btn btn-outline btn-sm" data-action="customer-detail" data-id="' + user.id + '">View</button> <button class="btn btn-outline btn-sm" data-action="customer-active" data-id="' + user.id + '" data-active="' + (!user.is_active) + '">' + (user.is_active ? 'Deactivate' : 'Activate') + '</button></td></tr>'; }).join("") +
    '</tbody></table></div></div>';
}

function adminSettings() {
  const settings = state.settings || {};
  const promos = state.promos || [];
  return '<div class="dash-card"><div class="dash-card-head"><h3>Hotel details</h3></div><div class="field"><label>Hotel name</label><input id="hotel-name" value="' + esc(settings.hotel_name || 'StayEase Hotel') + '"></div><div class="field"><label>Default tax rate (%)</label><input id="tax-rate" type="number" value="' + esc(settings.tax_rate || '12') + '"></div><div class="field"><label>Currency</label><input id="currency" value="' + esc(settings.currency || 'USD') + '"></div><button class="btn btn-primary" data-action="save-settings">Save settings</button></div><div class="dash-card"><div class="dash-card-head"><h3>Promotional codes</h3><button class="btn btn-outline btn-sm" data-action="add-promo">＋ Add code</button></div>' +
    promos.map(function(promo) { return '<div class="booking-row"><div><strong>' + esc(promo.code) + '</strong><small>' + promo.discount_percent + '% off · ' + promo.min_nights + ' night minimum · ' + promo.used_count + '/' + promo.max_uses + ' uses</small></div><span class="tag ' + (promo.is_active ? 'green' : 'red') + '">' + (promo.is_active ? 'Active' : 'Paused') + '</span><button class="btn btn-outline btn-sm" data-action="toggle-promo" data-id="' + promo.id + '" data-active="' + (!promo.is_active) + '">' + (promo.is_active ? 'Pause' : 'Activate') + '</button><button class="btn btn-danger btn-sm" data-action="delete-promo" data-id="' + promo.id + '">×</button></div>'; }).join("") + '</div>';
}

function roomCard(room) {
  const name=esc(room.name), type=esc(room.type), description=esc(room.description||""), emoji=esc(room.emoji||"🛏️");
  const amenities=(room.amenities||[]).slice(0,3).map(function(item){return '<span class="tag">'+esc(item)+'</span>';}).join("");
  return '<article class="room-card"><div class="room-art" style="background:'+room.art+'"><span class="art-emoji">'+emoji+'</span><span class="tag '+(room.status==="Available"?"green":"red")+'">'+esc(room.status)+'</span><button class="heart '+(state.favorites.has(room.id)?"active":"")+'" data-action="favorite" data-id="'+room.id+'" aria-label="Toggle favorite">'+(state.favorites.has(room.id)?"♥":"♡")+'</button></div><div class="room-body"><div class="room-meta"><span>'+type+' · Up to '+Number(room.capacity)+' guests</span><span class="rating">★ '+Number(room.rating||0).toFixed(1)+' <span class="muted">('+Number(room.reviews||0)+')</span></span></div><h3>'+name+'</h3><p>'+description.slice(0,108)+(description.length>108?"…":"")+'</p><div class="amenity-tags">'+amenities+'</div><div class="room-foot"><span class="price">'+money(room.price)+' <small>/ night</small></span><div class="room-actions"><button class="btn btn-outline btn-sm" data-page="details" data-id="'+room.id+'">View</button><button class="btn btn-primary btn-sm" data-action="book" data-id="'+room.id+'">Book</button></div></div></div></article>';
}

function testimonialCard() {
  if(!reviews.length)return '<article class="testimonial"><div class="stars">★★★★★</div><blockquote>We look forward to welcoming you and hearing about your stay.</blockquote><div class="guest"><div class="avatar">SE</div><div><strong>StayEase</strong><small>Guest experiences</small></div></div></article>';
  const item=reviews[state.testimonial%reviews.length];
  return '<article class="testimonial"><div class="stars">'+('★'.repeat(Math.max(1,Math.min(5,Number(item.rating||5)))))+'</div><blockquote>“'+esc(item.text||item.comment||"")+'”</blockquote><div class="guest"><div class="avatar">'+initials(item.name||item.user||"Guest")+'</div><div><strong>'+esc(item.name||item.user||"Guest")+'</strong><small>'+esc(item.date||"StayEase guest")+'</small></div></div></article>';
}

function navbar() {
  const user=state.user,unread=(state.notificationsList||[]).filter(function(item){return !item.is_read;}).length;
  const auth=user?'<button class="icon-btn" data-action="notifications" aria-label="Notifications">♧'+(unread?'<small>'+unread+'</small>':'')+'</button><span class="role-pill">'+esc(user.role)+'</span><button class="btn btn-ghost btn-sm guest-only" data-page="dashboard">'+(user.role==="admin"?"Admin":"My stay")+'</button><button class="btn btn-outline btn-sm guest-only" data-action="logout">Sign out</button>':'<button class="btn btn-ghost btn-sm guest-only" data-page="login">Sign in</button><button class="btn btn-primary btn-sm guest-only" data-page="register">Join us</button>';
  const notes=(state.notificationsList||[]).map(function(item){return '<button class="notification" data-action="read-notification" data-id="'+item.id+'" style="border:0;background:transparent;text-align:left;color:inherit"><span>✦</span><span><b>'+esc(item.title)+'</b><small>'+esc(item.message)+'</small></span></button>';}).join("");
  return '<header class="topbar" id="topbar"><div class="wrap nav-inner"><a class="brand" href="#" data-page="home" aria-label="StayEase home"><span class="brand-icon">🏨</span><span><span class="stay">Stay</span><span class="ease">Ease</span></span></a><nav class="nav-links"><a href="#" data-page="home" class="'+(state.page==="home"?"active":"")+'">Home</a><a href="#" data-page="rooms" class="'+(state.page==="rooms"?"active":"")+'">Stay with us</a><a href="#amenities" data-scroll="amenities">Experiences</a><a href="#footer" data-scroll="footer">Our story</a></nav><div class="nav-actions"><button class="icon-btn" data-action="theme" aria-label="Toggle color theme">'+(state.theme==="dark"?"☀":"☾")+'</button>'+auth+'<button class="icon-btn hamburger" data-action="mobile" aria-label="Open menu">☰</button></div></div><div class="mobile-links '+(state.mobile?"open":"")+'"><a href="#" data-page="home">Home</a><a href="#" data-page="rooms">Stay with us</a><a href="#amenities" data-scroll="amenities">Experiences</a>'+(user?'<a href="#" data-page="dashboard">'+(user.role==="admin"?"Admin dashboard":"My stay")+'</a><button data-action="logout">Sign out</button>':'<a href="#" data-page="login">Sign in</a><a href="#" data-page="register">Join us</a>')+'</div></header>'+(state.notifications&&user?'<div class="modal-backdrop" data-action="close-notifications"><div class="modal" style="position:absolute;right:7%;top:82px;width:340px" data-stop><div class="modal-head"><h2>For you</h2><button class="icon-btn" data-action="notifications">×</button></div><div class="modal-body">'+(notes||'<p class="muted">You are all caught up.</p>')+'</div><div class="modal-foot"><button class="btn btn-ghost btn-sm" data-action="read-all-notifications">Mark all as read</button><button class="btn btn-outline btn-sm" data-action="close-notifications">Close</button></div></div></div>':'');
}

function calendarHTML(room) {
  const today=new Date(), year=today.getFullYear(), month=today.getMonth(), first=new Date(year,month,1).getDay(), count=new Date(year,month+1,0).getDate(), blocked=new Set(room.booked||[]);
  let cells="";
  for(let i=0;i<first;i++)cells+='<span></span>';
  for(let day=1;day<=count;day++)cells+='<span class="'+(blocked.has(day)?"busy":"free")+'" aria-label="'+(blocked.has(day)?"Booked":"Available")+' '+day+'" style="font-size:10px;padding:7px 0">'+day+'</span>';
  return '<div class="dash-card" style="padding:15px;max-width:390px"><div style="display:grid;grid-template-columns:repeat(7,1fr);text-align:center;margin-bottom:5px">'+['S','M','T','W','T','F','S'].map(function(d){return '<span class="muted" style="font-size:9px;padding:5px">'+d+'</span>';}).join("")+cells+'</div><div style="display:flex;gap:13px;font-size:9px;color:var(--muted)"><span><i style="display:inline-block;width:8px;height:8px;background:var(--green-bg)"></i> Available</span><span><i style="display:inline-block;width:8px;height:8px;background:var(--red-bg)"></i> Booked</span></div></div>';
}

function detailsPage() {
  const room=getRoom(state.roomId)||rooms[0];
  if(!room)return '<section class="page"><div class="wrap"><p>Rooms are loading.</p></div></section>';
  const reviewsForRoom=(state.roomReviews||[]).map(function(item){return '<div class="review"><div class="review-head"><strong>'+esc(item.name||item.user||"StayEase guest")+'</strong><span class="rating">'+("★".repeat(Number(item.rating||0)))+'</span></div><p>'+esc(item.comment||item.text||"")+'</p></div>';}).join("");
  return '<section class="page"><div class="wrap"><button class="btn btn-ghost btn-sm" data-page="rooms">← Back to rooms</button><div class="detail-layout" style="margin-top:15px"><div><div class="gallery"><div class="detail-art" style="background:'+room.art+'">'+esc(room.emoji)+'</div><div class="detail-art" style="background:linear-gradient(135deg,#dac7a8,#98856b)">🛏️</div><div class="detail-art" style="background:linear-gradient(135deg,#c3d6c0,#759276)">🌿</div><div class="detail-art" style="background:linear-gradient(135deg,#e2d4bf,#bd9f79)">🛁</div><div class="detail-art" style="background:linear-gradient(135deg,#b8cfd3,#779ba0)">☕</div></div><div class="detail-copy"><div class="room-meta" style="margin-top:20px"><span>'+esc(room.type)+' · Up to '+room.capacity+' guests</span><span class="rating">★ '+Number(room.rating||0).toFixed(1)+' <span class="muted">('+Number(room.reviews||0)+' reviews)</span></span></div><h1>'+esc(room.name)+'</h1><p>'+esc(room.description)+'</p><h3>Thoughtful comforts</h3><div class="amenities-full">'+(room.amenities||[]).map(function(name){return '<span>✧ '+esc(name)+'</span>';}).join("")+'</div><h3>A few helpful notes</h3><div class="rules-grid"><div class="rule">↗ Check-in from 3:00 PM · Check-out by 11:00 AM</div><div class="rule">♡ Cancellation refunds depend on arrival time</div><div class="rule">⌂ Non-smoking room</div><div class="rule">♧ Daily housekeeping</div></div><h3>Availability · '+new Date().toLocaleDateString(undefined,{month:"long",year:"numeric"})+'</h3>'+calendarHTML(room)+'<h3>Guest reviews</h3>'+(reviewsForRoom||'<p class="muted">No reviews for this room yet.</p>')+(state.user?'<button class="btn btn-outline" style="margin-top:14px" data-action="write-review">Write a review</button>':'<p class="muted">Sign in after a stay to share your review.</p>')+'</div></div><aside class="booking-card"><div class="room-meta"><span>Starting at</span>'+statusTag(room.status)+'</div><div class="price" style="margin-top:7px">'+money(room.price)+' <small>/ night</small></div><div class="field"><label>Check in</label><input type="date" id="detail-in" min="'+todayISO()+'" value="'+datePlus(1)+'"></div><div class="field"><label>Check out</label><input type="date" id="detail-out" min="'+datePlus(2)+'" value="'+datePlus(2)+'"></div><div class="field"><label>Guests</label><select id="detail-guests">'+Array.from({length:room.capacity},function(_,i){return '<option value="'+(i+1)+'">'+(i+1)+' guest'+(i?'s':'')+'</option>';}).join("")+'</select></div><div class="summary-line"><span>Estimated total · 1 night + tax</span><strong id="detail-total">'+money(Math.round(room.price*1.12))+'</strong></div><button class="btn btn-primary" data-action="book" data-id="'+room.id+'">Reserve your stay　→</button><small class="muted" style="display:block;text-align:center;margin-top:10px">Final price confirmed before payment</small></aside></div></div></section>';
}

function adminReports() {
  const stats=state.adminStats||{}, types=Object.entries(stats.room_type_performance||{}), max=Math.max(1,...types.map(function(item){return Number(item[1]);}));
  return '<div class="dash-stats admin-stats">'+[['Total revenue',money(stats.total_revenue||0)],['Active bookings',stats.active_bookings||0],['Cancellation rate',Number(stats.cancellation_rate||0)+'%'],['Total customers',stats.total_customers||0]].map(function(item){return '<div class="dash-stat"><span>'+item[0]+'</span><strong>'+item[1]+'</strong></div>';}).join("")+'</div><div class="dash-card"><div class="dash-card-head"><h3>Revenue by room type</h3><span class="tag gold">Completed stays</span></div>'+(types.length?types.map(function(item){return '<div style="display:grid;grid-template-columns:85px 1fr 80px;gap:12px;align-items:center;margin:15px 0;font-size:11px"><span>'+esc(item[0])+'</span><div class="progress" style="margin:0;background:var(--line)"><span style="width:'+(Number(item[1])/max*100)+'%"></span></div><strong>'+money(item[1])+'</strong></div>';}).join(""):'<p class="muted">No completed stay revenue yet.</p>')+'</div>';
}

function adminSettings() {
  const settings=state.settings||{}, promos=state.promos||[];
  return '<div class="dash-card"><div class="dash-card-head"><h3>Hotel details</h3></div><div class="field"><label>Hotel name</label><input id="hotel-name" value="'+esc(settings.hotel_name||"StayEase Hotel")+'"></div><div class="field"><label>Default tax rate (%)</label><input id="tax-rate" type="number" value="'+esc(settings.tax_rate||"12")+'"></div><div class="field"><label>Currency</label><input id="currency" value="'+esc(settings.currency||"USD")+'"></div><button class="btn btn-primary" data-action="save-settings">Save settings</button></div><div class="dash-card"><div class="dash-card-head"><h3>Promotional codes</h3><button class="btn btn-outline btn-sm" data-action="add-promo">＋ Add code</button></div>'+promos.map(function(p){return '<div class="booking-row"><div><strong>'+esc(p.code)+'</strong><small>'+Number(p.discount_percent)+'% off · '+Number(p.min_nights)+' night minimum · '+p.used_count+'/'+p.max_uses+' uses</small></div><span class="tag '+(p.is_active?"green":"red")+'">'+(p.is_active?"Active":"Paused")+'</span><button class="btn btn-outline btn-sm" data-action="toggle-promo" data-id="'+p.id+'" data-active="'+(!p.is_active)+'">'+(p.is_active?"Pause":"Activate")+'</button><button class="btn btn-danger btn-sm" data-action="delete-promo" data-id="'+p.id+'">×</button></div>';}).join("")+'</div>';
}

function revenueChart() {
  const stats=state.adminStats||{}, values=Object.entries(stats.revenue_by_month||{}).sort(function(a,b){return a[0].localeCompare(b[0]);}).slice(-12);
  if(!values.length)return '<div class="empty-state"><p>No completed stays are available for the chart.</p></div>';
  const max=Math.max(1,...values.map(function(item){return Number(item[1]);})),step=550/values.length;
  const labels=values.map(function(item){const parts=item[0].split("-").map(Number);return new Date(parts[0],parts[1]-1,1).toLocaleDateString(undefined,{month:"short"});});
  const bars=values.map(function(item,i){const value=Number(item[1]),height=value/max*150;return '<rect class="chart-bar" x="'+(48+i*step)+'" y="'+(195-height)+'" width="'+Math.max(12,step*.55)+'" height="'+height+'"><title>'+labels[i]+' · '+money(value)+'</title></rect><text x="'+(42+i*step)+'" y="216">'+labels[i]+'</text>';}).join("");
  return '<div class="chart"><svg viewBox="0 0 600 220" role="img" aria-label="Revenue by month"><path class="chart-grid" d="M40 20H590M40 65H590M40 110H590M40 155H590M40 200H590"/>'+bars+'</svg></div>';
}

function customerReviews() {
  const mine=state.myReviews||[];
  return '<div class="dash-card"><div class="dash-card-head"><h3>Your notes from the road</h3></div>'+(mine.length?mine.map(function(item){const room=getRoom(item.room_id);return '<div class="review"><strong>'+("★".repeat(item.rating))+' · '+esc(room?room.name:"StayEase stay")+'</strong><small>'+esc(new Date(item.created_at).toLocaleDateString())+'</small><p>'+esc(item.comment||"")+'</p></div>';}).join(""):'<div class="empty-state"><div>✎</div><h3 class="serif">Your next story is still unwritten.</h3><p>After checkout, share a review from a completed stay.</p></div>')+'</div>';
}

function customerDashboard() {
  const active=bookings.filter(function(item){return item.status==="Confirmed"||item.status==="Checked In";});
  const history=bookings.filter(function(item){return item.status==="Completed";});
  const spend=history.reduce(function(total,item){return total+Number(item.total||0);},0);
  let body="";
  if(state.customerTab==="Bookings")body=customerBookings();
  if(state.customerTab==="Favorites")body=customerFavorites();
  if(state.customerTab==="Reviews")body=customerReviews();
  if(state.customerTab==="Loyalty")body=customerLoyalty();
  if(state.customerTab==="Profile")body=customerProfile();
  return '<section class="page"><div class="wrap"><div class="dash-layout">'+dashSide()+'<div class="dash-main"><h1>Good '+(new Date().getHours()<12?"morning":"day")+', '+esc((state.user.name||"Guest").split(" ")[0])+'.</h1>'+(state.customerTab==="Bookings"?'<div class="dash-stats">'+[['Your stays',bookings.length],['Coming up',active.length],['Lifetime spend',money(spend)],['StayEase points',Number(state.user.points||0)]].map(function(item){return '<div class="dash-stat"><span>'+item[0]+'</span><strong>'+item[1]+'</strong></div>';}).join("")+'</div>':'')+body+'</div></div></div></section>';
}

function customerBookings() {
  const groups=state.bookingTab==="Upcoming"?bookings.filter(function(item){return item.status==="Confirmed"||item.status==="Checked In";}):state.bookingTab==="Past"?bookings.filter(function(item){return item.status==="Completed";}):state.bookingTab==="Cancelled"?bookings.filter(function(item){return item.status==="Cancelled";}):bookings;
  const tabs=["Upcoming","Past","Cancelled","All"].map(function(tab){return '<button class="'+(state.bookingTab===tab?"active":"")+'" data-action="booking-tab" data-tab="'+tab+'">'+tab+'</button>';}).join("");
  const rows=groups.map(function(item){
    const action=item.status==="Confirmed"?'<button class="btn btn-outline btn-sm" data-action="modify-booking" data-id="'+esc(item.id)+'">Modify</button> <button class="btn btn-danger btn-sm" data-action="cancel-booking" data-id="'+esc(item.id)+'">Cancel</button>':"";
    return '<div class="booking-row"><div><strong>'+esc(item.room)+'</strong><small>Reservation '+esc(item.id)+'</small></div><div>'+esc(item.dates)+'<small>Your reservation</small></div><div>'+statusTag(item.status)+'<small>'+money(item.total)+' total</small></div><div>'+action+'</div></div>';
  }).join("");
  return '<div class="dash-card"><div class="dash-card-head"><h3>Your stays</h3><button class="btn btn-primary btn-sm" data-page="rooms">Find a room　→</button></div><div class="tabbar">'+tabs+'</div>'+(rows||'<div class="empty-state"><div>✧</div><h3 class="serif">Nothing here for now.</h3><p>Your next favorite stay could be just around the corner.</p><button class="btn btn-primary" data-page="rooms">Explore rooms</button></div>')+'</div><div class="dash-card"><div class="dash-card-head"><h3>For your next getaway</h3><span class="tag gold">A little treat</span></div><p class="muted" style="font-size:12px">Use your member code <strong style="color:var(--gold-dark)">STAY15</strong> for 15% off a stay of three nights or more.</p></div>';
}

function customerLoyalty() {
  const points=Number(state.user.loyalty_points||state.user.points||0),tier=state.user.loyalty_tier||"Silver";
  const next=tier==="Silver"?1000:tier==="Gold"?5000:5000,progress=tier==="Platinum"?100:Math.min(100,points/next*100),remaining=Math.max(0,next-points);
  const history=state.loyaltyHistory||[];
  return '<div class="loyalty"><div class="loyalty-box"><span class="eyebrow" style="color:#e8c97a">StayEase Circle</span><h2 class="serif" style="font-size:31px;margin:12px 0">'+esc(tier)+' member</h2><p style="font-size:11px;color:#ffffffad">Thoughtful little extras, just for you.</p><div style="font:600 25px Playfair Display">'+points.toLocaleString()+' <small style="font:11px DM Sans">points</small></div><div class="progress"><span style="width:'+progress+'%"></span></div><small style="color:#ffffffaa">'+(tier==="Platinum"?"You have reached the top tier.":remaining.toLocaleString()+" points to "+(tier==="Silver"?"Gold":"Platinum"))+'</small></div><div class="dash-card"><h3>Member benefits</h3><p class="muted" style="font-size:11px;line-height:1.6">'+(tier==="Platinum"?"Enjoy a 10% loyalty discount on eligible stays.":tier==="Gold"?"Enjoy a 5% loyalty discount on eligible stays.":"Earn one point per dollar after checkout and unlock member savings.")+'</p></div></div><div class="dash-card" style="margin-top:15px"><div class="dash-card-head"><h3>Points history</h3></div>'+(history.length?history.map(function(item){return '<div class="booking-row"><div><strong>'+esc(item.reason)+'</strong><small>'+esc(new Date(item.created_at).toLocaleDateString())+'</small></div><strong class="tag green">+'+Number(item.points).toLocaleString()+'</strong></div>';}).join(""):'<div class="empty-state"><p>Points earned after checkout will show here.</p></div>')+'</div>';
}

async function downloadCalendar() {
  const draft=state.bookingDraft;
  try { const response=await api.calendar(draft.bookingId); download("stayease-"+draft.bookingId+".ics",await response.text(),"text/calendar"); }
  catch(error) { toast(error.message,"error"); }
}

function calcDraft() {
  const draft=state.bookingDraft||{},room=getRoom(draft.roomId)||rooms[0];
  if(!room)return {r:{name:"Room",price:0,emoji:"🛏️"},n:1,subtotal:0,discount:0,tax:0,total:0};
  if(draft.quote)return {r:room,n:draft.quote.nights,subtotal:draft.quote.subtotal,discount:draft.quote.discount_amount,tax:draft.quote.tax_amount,total:draft.quote.total};
  const count=nights(draft.checkin,draft.checkout),subtotal=room.price*count+(draft.extras||[]).reduce(function(sum,name){return sum+({Breakfast:24,"Airport pickup":48,"Late checkout":35,"Spa package":95}[name]||0)*count;},0),discount=Math.round(subtotal*(draft.discount||0)),tax=Math.round((subtotal-discount)*.12);
  return {r:room,n:count,subtotal:subtotal,discount:discount,tax:tax,total:subtotal-discount+tax};
}

async function updateDetailQuote() {
  if (!state.user || state.page !== "details") return;
  const checkin=$("#detail-in")?.value,checkout=$("#detail-out")?.value;
  if(!checkin||!checkout||checkout<=checkin)return;
  try {
    const quote=await api.quote({roomId:state.roomId,checkin:checkin,checkout:checkout,guests:Number($("#detail-guests")?.value||1)});
    const total=$("#detail-total");if(total)total.textContent=money(quote.total);
  } catch(error) { toast(error.message,"error"); }
}

async function nextBookingStep() {
  const draft=state.bookingDraft;
  if(state.bookingStep===1){
    const checkin=$("#book-in").value,checkout=$("#book-out").value;
    if(!checkin||!checkout||checkout<=checkin){toast("Check-out needs to be after check-in.","error");return;}
    draft.checkin=checkin;draft.checkout=checkout;draft.guests=Number($("#book-guests").value);
    try{draft.quote=await api.quote(draft);}catch(error){toast(error.message,"error");return;}
    state.bookingStep=2;render();return;
  }
  if(state.bookingStep===2){try{draft.quote=await api.quote(draft);}catch(error){toast(error.message,"error");return;}state.bookingStep=3;render();return;}
  if(state.bookingStep===3){
    draft.payment=$("#payment-method").value;draft.guest=$("#book-guest").value.trim();draft.email=$("#book-email").value.trim();draft.card=$("#card-number")?.value||"";
    if(!draft.guest||! /^\S+@\S+\.\S+$/.test(draft.email)){toast("Please add a name and valid email address.","error");return;}
    if(draft.payment!=="Pay at the hotel"&&(draft.card.replace(/\D/g,"").length<15||! /^\d{2}\/\d{2}$/.test($("#card-expiry")?.value||"")||!$("#card-cvc")?.value)){toast("Please complete the card details.","error");return;}
    const button=$(".modal-foot .btn-primary");if(button){button.disabled=true;button.textContent="Securing your stay…";}
    try{draft.quote=await api.quote(draft);const result=await api.createBooking(draft);draft.bookingId=result.id;bookings.unshift({...result,guest:draft.guest,email:draft.email,roomId:draft.roomId,status:"Confirmed"});state.bookingStep=4;render();}
    catch(error){toast(error.message,"error");if(button){button.disabled=false;button.textContent="Confirm and reserve";}}
  }
}

document.addEventListener("click", async function(event) {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  const action = button.dataset.action, id = button.dataset.id;
  const stop = function() { event.preventDefault(); event.stopImmediatePropagation(); };
  try {
    if (action === "approve-booking" || action === "checkout-booking") {
      stop(); await api.updateBookingStatus(id, action === "approve-booking" ? "checked_in" : "checked_out"); await loadDashboardData(); toast("Reservation status updated.", "success"); return;
    }
    if (action === "admin-cancel") {
      stop(); await api.cancelBooking(id); await loadDashboardData(); toast("Reservation cancelled.", "success"); return;
    }
    if (action === "forgot-submit") {
      stop(); const email=$("#forgot-email")?.value||"";const result=await api.forgotPassword(email);state.modal=null;render();toast(result.message,"success");return;
    }
    if (action === "export-csv") {
      stop(); const blob = await api.exportBookings(); download("stayease-bookings.csv", blob, "text/csv"); return;
    }
    if (action === "save-settings") {
      stop(); state.settings = await api.saveSettings({ hotel_name: $("#hotel-name").value, tax_rate: $("#tax-rate").value, currency: $("#currency").value.toUpperCase() }); render(); toast("Hotel settings saved.", "success"); return;
    }
    if (action === "apply-promo") {
      stop(); const code=$("#promo-input")?.value||"", nightsCount=nights(state.bookingDraft.checkin,state.bookingDraft.checkout);
      const result=await api.applyPromo(code,nightsCount);state.bookingDraft.promo=code.toUpperCase();state.bookingDraft.discount=result.discount;state.bookingDraft.quote=null;render();toast(code.toUpperCase()+" applied — "+result.percent+"% off.","success");return;
    }
    if (action === "read-notification") {
      stop(); await api.markNotificationRead(id); state.notificationsList=state.notificationsList.map(function(item){return item.id===Number(id)?{...item,is_read:true}:item;}); render(); return;
    }
    if (action === "read-all-notifications") {
      stop(); await api.markAllNotificationsRead(); state.notificationsList=state.notificationsList.map(function(item){return {...item,is_read:true};}); render(); return;
    }
    if (action === "save-profile") {
      stop(); state.user=await api.updateProfile({name:$("#profile-name").value,phone:$("#profile-phone").value});state.profileEdit=false;render();toast("Your details have been saved.","success");return;
    }
    if (action === "modify-booking") {
      stop(); state.modifyBookingId=id;state.modal={kind:"generic",title:"Modify your dates",submit:true,body:'<div class="field"><label>New check in</label><input id="modify-in" type="date" value="'+datePlus(2)+'"></div><div class="field"><label>New check out</label><input id="modify-out" type="date" value="'+datePlus(4)+'"></div>'};render();return;
    }
    if (action === "add-room") {
      stop(); state.roomEditingId = null; state.modal = { kind:"generic", title:"Add a room", submit:true, body:'<div class="field"><label>Room number</label><input id="new-room-number" required></div><div class="field"><label>Room name</label><input id="new-room-name" required></div><div class="field"><label>Room type</label><select id="new-room-type"><option>Standard</option><option>Deluxe</option><option>Suite</option></select></div><div class="field"><label>Nightly rate</label><input id="new-room-price" type="number" min="0"></div><div class="field"><label>Guest capacity</label><input id="new-room-capacity" type="number" min="1" value="2"></div><div class="field"><label>Amenities, separated by commas</label><input id="new-room-amenities" value="WiFi, AC, TV"></div>' }; render(); return;
    }
    if (action === "edit-room") {
      stop(); const room = getRoom(id); if (!room) return; state.roomEditingId = Number(id);
      state.modal = { kind:"generic", title:"Edit " + room.name, submit:true, body:'<div class="field"><label>Room number</label><input id="edit-room-number" value="' + esc(room.room_number) + '"></div><div class="field"><label>Room name</label><input id="edit-room-name" value="' + esc(room.name) + '"></div><div class="field"><label>Nightly rate</label><input id="edit-room-price" type="number" value="' + room.price + '"></div><div class="field"><label>Room type</label><select id="edit-room-type"><option>Standard</option><option>Deluxe</option><option>Suite</option></select></div><div class="field"><label>Capacity</label><input id="edit-room-capacity" type="number" value="' + room.capacity + '"></div><div class="field"><label>Amenities, separated by commas</label><input id="edit-room-amenities" value="' + esc((room.amenities || []).join(", ")) + '"></div>' };
      render(); const type = $("#edit-room-type"); if (type) type.value = room.type; return;
    }
    if (action === "delete-room") {
      stop(); if (!confirm("Remove this room? Upcoming reservations prevent removal.")) return;
      await api.deleteRoom(id); rooms.splice(0, rooms.length, ...await api.getRooms()); render(); toast("Room removed.", "success"); return;
    }
    if (action === "customer-detail") {
      stop(); const info = await api.getCustomer(id), user = info.user;
      state.modal = { kind:"generic", title:user.name, body:'<p class="muted">' + esc(user.email) + ' · ' + esc(user.phone || "No phone") + '</p><p>' + (user.loyalty_points || 0) + ' loyalty points · ' + esc(user.loyalty_tier || "Silver") + '</p>' + info.bookings.map(function(item) { return '<div class="booking-row"><div><strong>' + esc(item.room) + '</strong><small>' + esc(item.booking_ref) + '</small></div><div>' + esc(item.dates) + '</div><div>' + statusTag(item.status) + '</div></div>'; }).join("") };
      render(); return;
    }
    if (action === "customer-active") {
      stop(); await api.request("/admin/customers/" + id + "/active", { method:"PATCH", body:JSON.stringify({ is_active:button.dataset.active === "true" }) }); await loadDashboardData(); return;
    }
    if (action === "add-promo") {
      stop(); state.modal = { kind:"generic", title:"Add promotional code", submit:true, body:'<div class="field"><label>Promo code</label><input id="new-promo"></div><div class="field"><label>Discount percent</label><input id="new-promo-percent" type="number" value="10"></div><div class="field"><label>Minimum nights</label><input id="new-promo-nights" type="number" value="1"></div>' }; render(); return;
    }
    if (action === "toggle-promo" || action === "delete-promo") {
      stop(); const promo=(state.promos||[]).find(function(item){return item.id===Number(id);}); if(!promo)return;
      if(action==="delete-promo")await api.deletePromo(id);else await api.savePromo({...promo,is_active:button.dataset.active==="true"},id);
      state.promos=await api.getPromos();render();return;
    }
    if (action === "toggle-promo" || action === "delete-promo") {
      stop(); const promo = state.promos.find(function(item) { return item.id === Number(id); }); if (!promo) return;
      if (action === "delete-promo") await api.deletePromo(id); else await api.savePromo({ ...promo, is_active:button.dataset.active === "true" }, id);
      state.promos = await api.getPromos(); render(); return;
    }
    if (action === "generic-submit" && state.modal && state.modal.kind === "generic") {
      if (state.modal.title === "Share your experience") {
        stop();await api.submitReview({room:state.roomId,rating:Number($("#review-rating").value),text:$("#review-note").value});
        state.modal=null;await loadDashboardData();toast("Thank you for sharing your note.","success");return;
      }
      if (state.modal.title === "Change password") {
        stop(); await api.changePassword($("#old-password").value,$("#new-password").value);state.modal=null;render();toast("Password updated.","success");return;
      }
      if (state.modal.title === "Modify your dates") {
        stop(); const updated=await api.modifyBooking(state.modifyBookingId,$("#modify-in").value,$("#modify-out").value);bookings=bookings.map(function(item){return item.id===state.modifyBookingId?updated:item;});state.modal=null;render();toast("Reservation dates updated.","success");return;
      }
      if (state.modal.title === "Add promotional code") {
        stop(); await api.savePromo({code:$("#new-promo").value.toUpperCase(),discount_percent:Number($("#new-promo-percent").value),min_nights:Number($("#new-promo-nights")?.value||1),valid_to:new Date(Date.now()+365*86400000).toISOString(),max_uses:500,is_active:true});
        state.promos=await api.getPromos();state.modal=null;render();return;
      }
      if (state.modal.title === "Add a room" || state.modal.title.indexOf("Edit ") === 0) {
        stop(); const room = state.roomEditingId ? getRoom(state.roomEditingId) : null;
        const data = { room_number:room ? $("#edit-room-number").value : $("#new-room-number").value, name:room ? $("#edit-room-name").value : $("#new-room-name").value, room_type:room ? $("#edit-room-type").value : $("#new-room-type").value, description:room ? room.description : "", price_per_night:Number(room ? $("#edit-room-price").value : $("#new-room-price").value), capacity:Number(room ? $("#edit-room-capacity").value : $("#new-room-capacity").value), floor:room ? room.floor : 1, status:room ? room.status_code : "available", image_urls:room ? room.image_urls : ["🛏️"], amenities:(room ? $("#edit-room-amenities").value : $("#new-room-amenities").value).split(",").map(function(x) { return x.trim(); }).filter(Boolean) };
        if (room) await api.updateRoom(room.id, data); else await api.createRoom(data);
        rooms.splice(0, rooms.length, ...await api.getRooms()); state.modal = null; render(); toast("Room saved.", "success"); return;
      }
      if (state.modal.title === "Add promotional code") {
        stop(); await api.savePromo({ code:$("#new-promo").value.toUpperCase(), discount_percent:Number($("#new-promo-percent").value), min_nights:Number($("#new-promo-nights").value), valid_to:new Date(Date.now()+365*86400000).toISOString(), max_uses:500, is_active:true });
        state.promos = await api.getPromos(); state.modal = null; render(); return;
      }
    }
  } catch (error) { stop(); toast(error.message, "error"); }
}, true);

document.addEventListener("change", async function(event) {
  const target = event.target;
  if (target.id === "detail-in" || target.id === "detail-out" || target.id === "detail-guests") updateDetailQuote();
  if (target.dataset.roomStatus) {
    event.stopImmediatePropagation();
    try { await api.setRoomStatus(target.dataset.roomStatus, target.value); const room = getRoom(target.dataset.roomStatus); if (room) room.status = target.value; toast("Room status updated.", "success"); }
    catch (error) { toast(error.message, "error"); render(); }
  }
  if (target.dataset.extra && state.bookingDraft) state.bookingDraft.quote = null;
  if (target.id === "admin-booking-status") { state.bookingsFilter = target.value; render(); }
  if (target.id === "booking-search") { state.bookingSearch = target.value; render(); }
}, true);

render();
